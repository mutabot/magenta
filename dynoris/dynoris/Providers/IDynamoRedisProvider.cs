using System.Collections.Generic;
using System.Threading.Tasks;

namespace dynoris
{
    public interface IDynamoRedisProvider
    {
        Task CacheItem(string cacheKey, string table, IList<(string, string)> storeKey);
        Task CommitItem(string key);
    }
}