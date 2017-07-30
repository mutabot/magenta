using Amazon.DynamoDBv2;
using dynoris;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using System;
using Xunit;

public class DatabaseFixture : IDisposable
{
    public DatabaseFixture()
    {
        var builder = new ConfigurationBuilder()
            .SetBasePath("..\\dynoris")
            .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
            .AddJsonFile($"appsettings.Development.json", optional: true)
            .AddEnvironmentVariables();

        var config = builder.Build();

        var services = new ServiceCollection();
        services.AddDefaultAWSOptions(config.GetAWSOptions());
        services.AddAWSService<IAmazonDynamoDB>();

        // Add framework services.
        services.AddSingleton<IDynamoRedisProvider, DynamoRedisProvider>();

        _provider = services.BuildServiceProvider();
    }

    public void Dispose()
    {
        // ... clean up test data from the database ...
    }

    public readonly IServiceProvider _provider;
    public ILogger<DynamoRedisProvider> log;
    public IConfiguration config;
    public IAmazonDynamoDB dynamo;
}

[CollectionDefinition("Database collection")]
public class DatabaseCollection : ICollectionFixture<DatabaseFixture>
{
    // This class has no code, and is never created. Its purpose is simply
    // to be the place to apply [CollectionDefinition] and all the
    // ICollectionFixture<> interfaces.
}
