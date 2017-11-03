using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using dynoris.Model;

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

        [HttpGet]
        [Route("api/Dynoris/CommitItem/{cacheKey}/{updateKey}")]
        public async Task<string> CommitItem([FromRoute] string cacheKey, [FromRoute] string updateKey)
        {
            _log.LogInformation($"Commit: {cacheKey}");
            return await _provider.CommitItem(cacheKey, updateKey);
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
        [Route("api/Dynoris/CacheAsHash")]
        public async Task CacheAsHash([FromBody] CacheItemRequest req)
        {
            _log.LogInformation($"As hash: {req.CacheKey} -> {req.Table}:{req.HashKey}");
            await _provider.CacheAsHash(req.CacheKey, req.Table, req.HashKey, req.StoreKey);
        }
    }
}
