using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace dynoris.Controllers
{
    public class CacheItemRequest
    {
        public string CacheKey { get; set; }
        public string Table { get; set; }
        public IList<(string, string)> StoreKey { get; set; }

        public string IndexName { get; set; }
        public string HashKey { get; set; }
    }
}
