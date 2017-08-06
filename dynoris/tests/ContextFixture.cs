using Amazon.DynamoDBv2;
using dynoris;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using StackExchange.Redis;
using System;
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
        services.AddSingleton<IDynamoRedisProvider, DynamoRedisProvider>();
        _provider = services.BuildServiceProvider();

        var loggerFactory = _provider.GetService<ILoggerFactory>();

        loggerFactory.AddConsole(configuration.GetSection("Logging"));
        loggerFactory.AddDebug();
        loggerFactory.AddFile(configuration.GetSection("Logging"));

        _redis = ConnectionMultiplexer.Connect(configuration.GetConnectionString("Redis"));
    }

    public void Dispose()
    {
        // ... clean up test data from the database ...
    }

    public readonly IServiceProvider _provider;
    public readonly ConnectionMultiplexer _redis;
}

[CollectionDefinition("Database collection")]
public class DatabaseCollection : ICollectionFixture<DatabaseFixture>
{
    // This class has no code, and is never created. Its purpose is simply
    // to be the place to apply [CollectionDefinition] and all the
    // ICollectionFixture<> interfaces.
}
