using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using dynoris;
using dynoris.Providers;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using StackExchange.Redis;
using System;
using System.Collections.Generic;
using Xunit;

public class DatabaseFixture : IDisposable
{
    public DatabaseFixture()
    {
        var builder = new ConfigurationBuilder()
            // .SetBasePath("..\\dynoris")
            .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
            .AddJsonFile($"appsettings.Development.json", optional: true)
            .AddEnvironmentVariables();

        var configuration = builder.Build();

        var services = new ServiceCollection();
        services.AddSingleton<IConfiguration>(configuration);
        services.AddLogging();
        var awsOptions = configuration.GetAWSOptions();
        Amazon.AWSConfigs.LoggingConfig.LogTo = Amazon.LoggingOptions.Console;

        services.AddDefaultAWSOptions(awsOptions);
        services.AddAWSService<IAmazonDynamoDB>();

        // Add framework services.
        services.AddSingleton<RedisServiceRecordProvider>();
        services.AddSingleton<IDynamoRedisProvider, DynamoRedisProvider>();
        _provider = services.BuildServiceProvider();

        var loggerFactory = _provider.GetService<ILoggerFactory>();

        loggerFactory.AddConsole(configuration.GetSection("Logging"));
        loggerFactory.AddDebug();
        loggerFactory.AddFile(configuration.GetSection("Logging"));

        _redis = ConnectionMultiplexer.Connect(configuration.GetConnectionString("Redis"));
        _dynamo = _provider.GetRequiredService<IAmazonDynamoDB>();

        // create dynamo table
        try
        {
            _dynamo.DeleteTableAsync("DynorisTests").Wait();
        }
        catch
        {
            // ignore as likely the table does not exists
        }
        _dynamo.CreateTableAsync(
            "DynorisTests",
            new List<KeySchemaElement>
            {
                    new KeySchemaElement("gid", KeyType.HASH)
            },
            new List<AttributeDefinition> { new AttributeDefinition("gid", ScalarAttributeType.S) },
            new ProvisionedThroughput(3, 3)
            ).Wait();
    }

    public void Dispose()
    {
        // ... clean up test data from the database ...
        try
        {
            _dynamo.DeleteTableAsync("DynorisTests").Wait();
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
