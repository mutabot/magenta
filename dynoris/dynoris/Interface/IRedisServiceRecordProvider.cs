using System.Threading.Tasks;
using StackExchange.Redis;

namespace dynoris.Providers
{
    public interface IRedisServiceRecordProvider
    {
        Task<bool> LinkBackOnRead(string cacheKey, DynamoLinkBag dlb);
        Task<DynamoLinkBag?> LinkBackOnWrite(string cacheKey);
        Task<bool> TouchKey(IDatabase db, string cacheKey);
    }
}