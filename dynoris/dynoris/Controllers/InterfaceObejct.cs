using System.Collections.Generic;

namespace dynoris.Controllers
{
    public class CacheItemRequest
    {
        public string CacheKey { get; set; }
        public string Table { get; set; }
        public IList<(string key, string value)> StoreKey { get; set; }

        public string IndexName { get; set; }
        public string HashKey { get; set; }
    }
}
