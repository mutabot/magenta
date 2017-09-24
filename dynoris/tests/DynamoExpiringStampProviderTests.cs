using dynoris;
using Microsoft.Extensions.DependencyInjection;
using System.Collections.Generic;
using Xunit;
using System;
using Amazon.DynamoDBv2.Model;
using System.Linq;

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
            var pastStamp = (DateTime.UtcNow - TimeSpan.FromSeconds(3)).ToDouble();
            var writeRequest = new BatchWriteItemRequest
            {
                RequestItems = new Dictionary<string, List<WriteRequest>>
                {
                    {
                        DynamoRedisProvider.TableName(DatabaseFixture.TestTableName),
                        Enumerable.Range(0, 10).Select(i =>
                            new WriteRequest
                            {
                                PutRequest = new PutRequest
                                {
                                    Item = new Dictionary<string, AttributeValue>
                                    {
                                        { "gid", new AttributeValue($"GID000{i:D3}") },
                                        { "active", new AttributeValue("Y") },
                                        { "updated", new AttributeValue { N = (pastStamp + i).ToString() } }
                                    }
                                }
                            }).
                            ToList()
                    }
                }
            };
            // add some values
            _fixture._dynamo.BatchWriteItemAsync(writeRequest).Wait();

            var storeKeys = new List<(string, string)>
            {
                ("active", "Y")
            };

            var items = _provider.Next(
                DatabaseFixture.TestTableName,
                DatabaseFixture.TestIndexName,
                storeKeys,
                ("updated", (pastStamp + 5).ToString())
            ).Result;

            Assert.True(items.Count == 5);
        }
    }
}
