using System.Collections.Generic;
using System.Threading.Tasks;

namespace dynoris
{
    public interface IDynamoExpiringStampProvider
    {
        /// <summary>
        /// Fetches all items matching storeKey condition where datetime stamp is past stampKey paramaters
        /// </summary>
        /// <param name="table">Table name</param>
        /// <param name="storeKey">Generic conditions</param>
        /// <param name="stampKey">Timestamp condition</param>
        /// <returns></returns>
        Task<List<string>> Next(string table, string indexName, IList<(string key, string value)> storeKey, (string key, string value) stampKey);
        /// <summary>
        /// Commits an item to an expiring stamp table
        /// </summary>
        /// <param name="table">Table name</param>
        /// <param name="storeKeys">Key conditions</param>
        /// <param name="itemJson"></param>
        /// <returns></returns>
        Task CommitItem(string table, IList<(string key, string value)> storeKeys, string itemJson);
    }
}