using System.Collections.Generic;
using System.Threading.Tasks;

namespace dynoris
{
    public interface IDynamoRedisProvider
    {
        /// <summary>
        /// Read the item from dynamo and store in Redis. Returns immediately if item is already cached in the Redis.
        /// Does no checks for the cacheKey relationship to dynamo query
        /// </summary>
        /// <param name="cacheKey">Redis string key name</param>
        /// <param name="table">Dynamo table</param>
        /// <param name="storeKey">Dynamo key(s)</param>
        /// <returns></returns>
        Task CacheItem(string cacheKey, string table, IList<(string key, string value)> storeKey);

        /// <summary>
        /// Read items from Dynamo and store in Redis hash. Returns immediately if item is already cached in the Redis.
        /// Does no checks for the cacheKey relationship to dynamo query
        /// </summary>
        /// <param name="cacheKey">Redis hash key name</param>
        /// <param name="table">Dynamo table name</param>
        /// <param name="indexName">Dynamo index name</param>
        /// <param name="hashKey">Key to be used as hash key</param>
        /// <param name="storeKey">Dynamo key(s)</param>
        /// <returns></returns>
        Task<long> CacheHash(string cacheKey, string table, string indexName, string hashKey, IList<(string key, string value)> storeKey);

        /// <summary>
        /// Read one item from Dynamo and store in Redis as a hash. Returns immediately if item is already cached in the Redis.
        /// Does no checks for the cacheKey relationship to dynamo query
        /// </summary>
        /// <param name="cacheKey">Redis hash key name</param>
        /// <param name="table">Dynamo table name</param>
        /// <param name="hashKey">Member to be used as hash key for list documents. Set to null for dictionary documents.</param>
        /// <param name="storeKey">Dynamo key(s)</param>
        /// <returns></returns>
        Task<long> CacheAsHash(string cacheKey, string table, string hashKey, IList<(string key, string value)> storeKey);

        /// <summary>
        /// Commits the item back to Dynamo. Returns immediately if item is still used elsewhere.
        /// </summary>
        /// <param name="cacheKey">Redis string key name</param>
        /// <returns>Old item Json for string items</returns>
        Task<string> CommitItem(string cacheKey);

        /// <summary>
        /// Deletes an item from the Redis and Dynamo
        /// </summary>
        /// <param name="cacheKey">Redis string or hash key name</param>
        /// <returns></returns>
        Task DeleteItem(string cacheKey);



    }
}