using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using dynoris.Model;
using Swashbuckle.AspNetCore.SwaggerGen;

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
        [SwaggerOperation(operationId: "CacheItem")]
        [Route("api/Dynoris/CacheItem", Name = "CacheItem")]
        public async Task CacheItem([FromBody] CacheItemRequest req)
        {
            await _provider.CacheItem(req.CacheKey, req.Table, req.StoreKey);
        }

        [HttpGet]
        [SwaggerOperation(operationId: "CommitItem")]
        [Route("api/Dynoris/CommitItem/{cacheKey}/{updateKey}", Name = "CommitItem")]
        public async Task<string> CommitItem([FromRoute] string cacheKey, [FromRoute] string updateKey)
        {
            _log.LogInformation($"Commit: {cacheKey}");
            return await _provider.CommitItem(cacheKey, updateKey);
        }

        [HttpPost]
        [SwaggerOperation(operationId: "DeleteItem")]
        [Route("api/Dynoris/DeleteItem", Name = "DeleteItem")]
        public async Task DeleteItem([FromBody] string cacheKey)
        {
            await _provider.DeleteItem(cacheKey);
        }

        [HttpPost]
        [SwaggerOperation(operationId: "CacheHash")]
        [Route("api/Dynoris/CacheHash", Name = "CacheHash")]
        public async Task CacheHash([FromBody] CacheItemRequest req)
        {
            await _provider.CacheHash(req.CacheKey, req.Table, req.IndexName, req.HashKey, req.StoreKey);
        }

        [HttpPost]
        [SwaggerOperation(operationId: "CacheAsHash")]
        [Route("api/Dynoris/CacheAsHash", Name = "CacheAsHash")]
        public async Task CacheAsHash([FromBody] CacheItemRequest req)
        {
            _log.LogInformation($"As hash: {req.CacheKey} -> {req.Table}:{req.HashKey}");
            await _provider.CacheAsHash(req.CacheKey, req.Table, req.HashKey, req.StoreKey);
        }
    }
}
