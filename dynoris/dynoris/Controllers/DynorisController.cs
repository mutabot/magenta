using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;

namespace dynoris.Controllers
{
    public class Dynoris : Controller
    {
        private readonly ILogger<Dynoris> _log;
        private readonly IDynamoRedisProvider _provider;

        public Dynoris(ILogger<Dynoris> log, IDynamoRedisProvider provider)
        {
            _log = log;
            _provider = provider;
        }

        [HttpPost]
        [Route("api/Dynoris/CacheItem")]
        public async Task CacheItem([FromBody] CacheItemRequest req)
        {
            await _provider.CacheItem(req.CacheKey, req.Table, req.StoreKey);
        }

        [HttpPost]
        [Route("api/Dynoris/CommitItem")]
        public async Task CommitItem([FromBody] string cacheKey)
        {
            await _provider.CommitItem(cacheKey);
        }

        [HttpPost]
        [Route("api/Dynoris/DeleteItem")]
        public async Task DeleteItem([FromBody] string cacheKey)
        {
            await _provider.DeleteItem(cacheKey);
        }

        [HttpPost]
        [Route("api/Dynoris/CacheHash")]
        public async Task CacheHash([FromBody] CacheItemRequest req)
        {
            await _provider.CacheHash(req.CacheKey, req.Table, req.IndexName, req.HashKey, req.StoreKey);
        }

        [HttpPost]
        [Route("api/Dynoris/CommitHash")]
        public async Task CommitHash([FromBody] string cacheKey)
        {
            await _provider.CommitItem(cacheKey);
        }

    }
}
