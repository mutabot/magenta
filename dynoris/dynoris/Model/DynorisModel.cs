using System;
using System.Collections.Generic;

namespace dynoris.Model
{
    public class CacheItemRequest
    {
        public string CacheKey { get; set; }
        public string Table { get; set; }
        public IList<(string key, string value)> StoreKey { get; set; }

        public string IndexName { get; set; }
        public string HashKey { get; set; }
    }

    public class ExpiringStampRequest
    {
        public string Table { get; set; }
        public string Index { get; set; }
        public IList<(string key, string value)> StoreKeys { get; set; }
        public (string key, string value) StampKey { get; set; }
    }

    public class CommitItemRequest
    {
        public string Table { get; set; }
        public IList<(string key, string value)> StoreKeys { get; set; }
        public string ItemJson { get; set; }
    }

}
