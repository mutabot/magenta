using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using StackExchange.Redis;
using System;
using System.Threading.Tasks;

namespace dynoris.Providers
{
    public class RedisServiceRecordProvider : IRedisServiceRecordProvider
    {
        private readonly ILogger _log;
        protected readonly ConnectionMultiplexer _redis;

        protected string _serviceKeySet = "dyno_bag:last_valid";
        protected string _serviceKeyHash = "dyno_bag:info";

        public TimeSpan ExpireTimeSpan { get; set; } = TimeSpan.FromSeconds(120); // default 2 minutes

        public RedisServiceRecordProvider(
            ILogger<RedisServiceRecordProvider> log,
            IConfiguration config,
            IRedisConnectionFactory redis)
        {
            _log = log;
            _redis = redis.Connection();
        }

        public async Task<bool> LinkBackOnRead(string cacheKey, DynamoLinkBag dlb)
        {
            var db = _redis.GetDatabase();

            // update link back record, this will set score to the expiry date time
            // NOTE: redis will remove the records after expiry
            return await TouchLinkBag(cacheKey, dlb, db);
        }

        /// <summary>
        /// Returns a DynamoLinkBag associated with this cacheKey. Will touch the key and extend its expiry.
        /// Purges expired service records.
        /// </summary>
        /// <param name="cacheKey"></param>
        /// <returns></returns>
        public async Task<DynamoLinkBag?> LinkBackOnWrite(string cacheKey)
        {
            var db = _redis.GetDatabase();

            // purge old records first
            await PurgeServicerecords(db);

            if (false == await TouchKey(db, cacheKey))
            {
                _log.LogWarning($"Key not foud (expired?): {cacheKey}");
                return null;
            }

            // read service record
            var linkStr = await db.HashGetAsync(_serviceKeyHash, cacheKey);
            if (!linkStr.HasValue)
            {
                throw new InvalidOperationException("Service record not found");
            }

            // update service record
            var dlb = JsonConvert.DeserializeObject<DynamoLinkBag>(linkStr);

            // update link back record, this will set score to twice the expire
            await TouchLinkBag(cacheKey, dlb, db);

            return dlb;
        }

        /// <summary>
        /// Will touch the service record and set the expiry timestamp
        /// </summary>
        /// <param name="cacheKey"></param>
        /// <param name="dlb"></param>
        /// <param name="db"></param>
        /// <returns></returns>
        private async Task<bool> TouchLinkBag(string cacheKey, DynamoLinkBag dlb, IDatabase db)
        {
            // set the sorted set record, adding expiry span to the last read
            await db.SortedSetAddAsync(_serviceKeySet, cacheKey, DateTime.UtcNow.Add(ExpireTimeSpan).ToDouble());

            var linkStr = JsonConvert.SerializeObject(dlb);
            await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);

            // set redis TTL on the record
            return await TouchKey(db, cacheKey);
        }

        public async Task<bool> TouchKey(IDatabase db, string cacheKey)
        {
            return await db.KeyExpireAsync(cacheKey, ExpireTimeSpan);
        }

        protected async Task PurgeServicerecords(IDatabase db)
        {
            // purge old records
            // NOTE the ExpirtTimeSpan adjust is to ensure redis expires records first
            var cutoffD = (DateTime.UtcNow - ExpireTimeSpan / 5).ToDouble();

            while (true)
            {
                var toPurge = await db.SortedSetRangeByScoreAsync(
                    _serviceKeySet,
                    0,
                    cutoffD,
                    Exclude.None,
                    Order.Ascending,
                    0,
                    64);

                if (toPurge.Length == 0)
                {
                    break;
                }

                // remove service records
                var removedSet = await db.SortedSetRemoveAsync(_serviceKeySet, toPurge);
                var removedHash = await db.HashDeleteAsync(_serviceKeyHash, toPurge);
            }
        }
    }
}
