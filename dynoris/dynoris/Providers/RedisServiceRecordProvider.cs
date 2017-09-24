using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using StackExchange.Redis;
using System;
using System.Threading.Tasks;

namespace dynoris.Providers
{
    public class RedisServiceRecordProvider
    {
        private readonly ILogger _log;
        protected readonly ConnectionMultiplexer _redis;

        protected string _serviceKeySet = "dyno_bag:last_valid";
        protected string _serviceKeyHash = "dyno_bag:info";

        public TimeSpan ExpireTimeSpan { get; set; } = TimeSpan.FromSeconds(600); // default 10 minutes

        public RedisServiceRecordProvider(ILogger<RedisServiceRecordProvider> log, IConfiguration config)
        {
            _log = log;
            _redis = ConnectionMultiplexer.Connect(config.GetConnectionString("Redis"));
        }

        public async Task<bool> LinkBackOnRead(string cacheKey, DynamoLinkBag dlb)
        {
            var db = _redis.GetDatabase();

            dlb.lastRead = DateTime.UtcNow;

            // update link back record, this will set score to twice the expire
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
            var now = DateTime.UtcNow;
            var db = _redis.GetDatabase();

            // purge old records first, NOTE the double expiry time to allow redis keys expire earlier
            await PurgeServicerecords(db, now - (ExpireTimeSpan + ExpireTimeSpan));

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
            dlb.lastRead = now;

            // update link back record, this will set score to twice the expire
            await TouchLinkBag(cacheKey, dlb, db);

            return dlb;
        }

        private async Task<bool> TouchLinkBag(string cacheKey, DynamoLinkBag dlb, IDatabase db)
        {
            await db.SortedSetAddAsync(_serviceKeySet, cacheKey, dlb.lastRead.Add(ExpireTimeSpan + ExpireTimeSpan).ToDouble());

            var linkStr = JsonConvert.SerializeObject(dlb);
            await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);

            return await TouchKey(db, cacheKey);
        }

        public async Task<bool> TouchKey(IDatabase db, string cacheKey)
        {
            return await db.KeyExpireAsync(cacheKey, ExpireTimeSpan);
        }

        public async Task PurgeServicerecords(IDatabase db, DateTime cutoff)
        {
            // purge old records
            var cutoffD = cutoff.ToDouble();

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
