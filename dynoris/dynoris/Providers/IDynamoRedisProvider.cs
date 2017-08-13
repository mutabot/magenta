using System.Collections.Generic;
using System.Threading.Tasks;

namespace dynoris
{
    public interface IDynamoRedisProvider
    {
        Task CacheItem(string cacheKey, string table, IList<(string, string)> storeKey);
        Task CommitItem(string cacheKey);

        Task DeleteItem(string table, IList<(string, string)> storeKey);
        Task DeleteItem(string cacheKey);

        Task<long> CacheHash(string cacheKey, string table, string indexName, string hashKey, IList<(string, string)> storeKey);
        Task<long> CommitHash(string cacheKey);
    }
}