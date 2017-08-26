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
        protected string _serviceKeyCount = "dyno_bag:ref_count";
//        protected string _serviceKeyCount = "dyno_bag:ref_count";

        public TimeSpan ExpireTimeSpan { get; set; } = TimeSpan.FromSeconds(60); // default 1 minute

        public RedisServiceRecordProvider(ILogger<RedisServiceRecordProvider> log, IConfiguration config)
        {
            _log = log;
            _redis = ConnectionMultiplexer.Connect(config.GetConnectionString("Redis"));
        }

        public async Task<long> LinkBackOnRead(string cacheKey, DynamoLinkBag dlb)
        {
            var db = _redis.GetDatabase();

            // increment and get ref count
            var refCount = await db.HashIncrementAsync(_serviceKeyCount, cacheKey);

            // create a record if ref count is 1
            if (refCount == 1)
            {
                dlb.refCount = refCount;
                dlb.lastRead = DateTime.UtcNow;

                var linkStr = JsonConvert.SerializeObject(dlb);

                // update link back record, set score to infinity to avoid deletion
                await db.SortedSetAddAsync(_serviceKeySet, cacheKey, double.MaxValue);
                await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);
            }

            // prevent item from expire
            await db.KeyPersistAsync(cacheKey);
            return refCount;
        }

        public async Task<DynamoLinkBag> LinkBackOnWrite(string cacheKey)
        {
            var now = DateTime.UtcNow;
            var db = _redis.GetDatabase();

            // purge old records first
            await PurgeServicerecords(db, now);

            // read service record
            var linkStr = await db.HashGetAsync(_serviceKeyHash, cacheKey);
            if (!linkStr.HasValue)
            {
                throw new InvalidOperationException("Service record not found");
            }

            // update service record
            var bag = JsonConvert.DeserializeObject<DynamoLinkBag>(linkStr);

            // decrement ref count
            bag.refCount = await db.HashDecrementAsync(_serviceKeyCount, cacheKey);
            bag.lastWrite = now;
            linkStr = JsonConvert.SerializeObject(bag);
            await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);

            // expire the record if ref count is exhausted and store the service records
            if (bag.refCount <= 0)
            {
                // set item to expire in (1 minute?)
                await db.KeyExpireAsync(cacheKey, ExpireTimeSpan);
                // set service record expiry
                await db.SortedSetAddAsync(_serviceKeySet, cacheKey, now.ToDouble());
            }

            return bag;
        }

        public async Task PurgeServicerecords(IDatabase db, DateTime now)
        {
            // purge old records
            var cutoffD = (now - ExpireTimeSpan).ToDouble();

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

                // check ref count
                foreach(var sr in toPurge)
                {
                    var refCount = await db.HashDecrementAsync(_serviceKeyCount, sr);
                    if (refCount >= 0)
                    {
                        _log.LogError($"Purging referenced key {sr}");
                    }
                    await db.HashDeleteAsync(_serviceKeyCount, sr);
                }

                var removedSet = await db.SortedSetRemoveAsync(_serviceKeySet, toPurge);
                var removedHash = await db.HashDeleteAsync(_serviceKeyHash, toPurge);
            }
        }
    }
}
