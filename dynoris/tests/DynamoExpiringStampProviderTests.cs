using dynoris;
using Microsoft.Extensions.DependencyInjection;
using Newtonsoft.Json.Linq;
using System.Collections.Generic;
using Xunit;
using System;

namespace tests
{
    [Collection("Database collection")]
    public partial class DynamoExpiringProviderTests
    {
        private readonly DatabaseFixture _fixture;
        private readonly IDynamoExpiringStampProvider _provider;
        public DynamoExpiringProviderTests(DatabaseFixture fixture)
        {
            _fixture = fixture;
            _provider = _fixture._provider.GetRequiredService<IDynamoExpiringStampProvider>();            
        }

        [Fact]
        public void NextExpiredSetTest()
        {
            var storeKeys = new List<(string, string)>
            {
                ("active", "true")
            };
            var stamp = DateTime.UtcNow.Ticks;

            var items = _provider.Next(
                DatabaseFixture.TestTableName, 
                DatabaseFixture.TestIndexName, 
                storeKeys,
                ("refreshStamp", stamp.ToString())
            ).Result;

            Assert.True(items.Count == 0);
        }
    }
}
