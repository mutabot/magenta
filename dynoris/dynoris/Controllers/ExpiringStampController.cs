using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using dynoris.Model;
using System.Collections.Generic;

namespace dynoris.Controllers
{
    public class ExpiringStampController : Controller
    {
        private readonly ILogger<ExpiringStampController> _log;
        private readonly IDynamoExpiringStampProvider _provider;

        public ExpiringStampController(ILogger<ExpiringStampController> log, IDynamoExpiringStampProvider provider)
        {
            _log = log;
            _provider = provider;
        }

        [HttpPost]
        [Route("api/ExpiringStamp/Next")]
        public async Task<List<string>> Next([FromBody] ExpiringStampRequest req)
        {
            return await _provider.Next(req.Table, req.Index, req.StoreKeys, req.StampKey);
        }

        [HttpPost]
        [Route("api/ExpiringStamp/CommitItem")]
        public async Task CommitItem([FromBody] CommitItemRequest req)
        {
            await _provider.CommitItem(req.Table, req.StoreKeys, req.ItemJson);
        }
    }
}
