using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using dynoris;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using StackExchange.Redis;
using System;
using System.Collections.Generic;
using Xunit;

public class DatabaseFixture : IDisposable
{
    public DatabaseFixture()
    {
        var builder = new ConfigurationBuilder()
                            .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
                            .AddJsonFile($"appsettings.Development.json", optional: true)
                            .AddEnvironmentVariables();

        var configuration = builder.Build();

        _provider = Startup.ConfigureDynorisServices(configuration, new ServiceCollection());

        _redis = ConnectionMultiplexer.Connect(configuration.GetConnectionString("Redis"));
        _dynamo = _provider.GetRequiredService<IAmazonDynamoDB>();

        // create dynamo table
        try
        {
            _dynamo.DeleteTableAsync(DynamoRedisProvider.TableName(TestTableName)).Wait();
        }
        catch
        {
            // ignore as likely the table does not exists
        }

        var req = new CreateTableRequest
        {
            TableName = DynamoRedisProvider.TableName(TestTableName),
            AttributeDefinitions = new List<AttributeDefinition>
            {
                new AttributeDefinition("gid", ScalarAttributeType.S),
                new AttributeDefinition("active", ScalarAttributeType.S),
                new AttributeDefinition("updated", ScalarAttributeType.N)
            },
            ProvisionedThroughput = new ProvisionedThroughput(3, 3),
            KeySchema = new List<KeySchemaElement>
            {
                new KeySchemaElement("gid", KeyType.HASH)
            },
            GlobalSecondaryIndexes = new List<GlobalSecondaryIndex>
            {
               new GlobalSecondaryIndex
               {
                   // index does not need to be prefixed
                   IndexName = TestIndexName,
                   KeySchema = new List<KeySchemaElement>
                   {
                       new KeySchemaElement("active", KeyType.HASH),
                       new KeySchemaElement("updated", KeyType.RANGE)
                   },
                   Projection = new Projection
                   {
                       ProjectionType = ProjectionType.INCLUDE,
                       NonKeyAttributes = new List<string> { "gid" }
                   },
                   ProvisionedThroughput = new ProvisionedThroughput(3, 3)
               }
            }
        };

        _dynamo.CreateTableAsync(req).Wait();
    }

    public static string TestTableName => "DynorisTests";
    public static string TestIndexName => "DynorisTestIndex";

    public void Dispose()
    {
        // ... clean up test data from the database ...
        try
        {
            _dynamo.DeleteTableAsync(DynamoRedisProvider.TableName(TestTableName)).Wait();
        }
        catch
        {
            // ignore
        }
    }

    public readonly IServiceProvider _provider;
    public readonly ConnectionMultiplexer _redis;
    public readonly IAmazonDynamoDB _dynamo;
}

[CollectionDefinition("Database collection")]
public class DatabaseCollection : ICollectionFixture<DatabaseFixture>
{
    // This class has no code, and is never created. Its purpose is simply
    // to be the place to apply [CollectionDefinition] and all the
    // ICollectionFixture<> interfaces.
}
