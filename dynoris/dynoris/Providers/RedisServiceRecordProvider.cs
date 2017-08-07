using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using StackExchange.Redis;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace dynoris.Providers
{
    public class RedisServiceRecordProvider
    {
        private readonly ILogger _log;
        protected readonly ConnectionMultiplexer _redis;

        protected string _serviceKeySet = "dyno_bag:set";
        protected string _serviceKeyHash = "dyno_bag:hash";

        public TimeSpan ExpireTimeSpan { get; set; } = TimeSpan.FromMinutes(1); // default 1 minute

        public RedisServiceRecordProvider(ILogger<RedisServiceRecordProvider> log, IConfiguration config)
        {
            _log = log;
            _redis = ConnectionMultiplexer.Connect(config.GetConnectionString("Redis"));

        }
        public async Task<IDatabase> LinkBackOnRead(string cacheKey, string table, IList<(string, string)> storeKey)
        {
            var bag = new DynamoLinkBag
            {
                table = table,
                storeKey = storeKey,
                lastRead = DateTime.UtcNow
            };

            var db = _redis.GetDatabase();

            var linkStr = JsonConvert.SerializeObject(bag);

            // update link back record, set score to infinity to avoid deletion
            var ssVal = new SortedSetEntry(cacheKey, double.MaxValue);
            await db.SortedSetAddAsync(_serviceKeySet, new SortedSetEntry[] { ssVal });
            await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);

            return db;
        }

        public async Task<DynamoLinkBag> LinkBackOnWrite(string cacheKey)
        {
            var now = DateTime.UtcNow;
            var db = _redis.GetDatabase();

            // purge old records first
            await PurgeServicerecords(db, now);

            // read service record
            var linkStr = await db.HashGetAsync(_serviceKeyHash, cacheKey);
            if (linkStr.HasValue)
            {
                var bag = JsonConvert.DeserializeObject<DynamoLinkBag>(linkStr);

                // update link back record
                bag.lastWrite = now;
                linkStr = JsonConvert.SerializeObject(bag);

                // store the service records
                var nowD = now.ToDouble();
                await db.SortedSetAddAsync(_serviceKeySet, cacheKey, nowD);
                await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);

                // set item to expire in 1 minute
                await db.KeyExpireAsync(cacheKey, TimeSpan.FromMinutes(1));
                return bag;
            }

            return null;
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
                var removedSet = await db.SortedSetRemoveAsync(_serviceKeySet, toPurge);
                var removedHash = await db.HashDeleteAsync(_serviceKeyHash, toPurge);
            }
        }
    }
}
