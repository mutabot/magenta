using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Amazon.DynamoDBv2;
using dynoris.Providers;
using System;
using Amazon;
using Swashbuckle.AspNetCore.Swagger;

namespace dynoris
{
    public class Startup
    {
        public Startup(IHostingEnvironment env)
        {
            var builder = new ConfigurationBuilder()
                .SetBasePath(env.ContentRootPath)
                .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
                .AddJsonFile($"appsettings.{env.EnvironmentName}.json", optional: true)
                .AddEnvironmentVariables();
            Configuration = builder.Build();
        }

        public IConfigurationRoot Configuration { get; }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            ConfigureDynorisServices(Configuration, services);

            // Add framework services.
            services.AddMvc();
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, ILoggerFactory loggerFactory)
        {
            loggerFactory.AddConsole(Configuration.GetSection("Logging"));
            loggerFactory.AddDebug();
            loggerFactory.AddFile(Configuration.GetSection("Logging"));

            app.UseSwagger();
            app.UseSwaggerUI(c =>
            {
                c.SwaggerEndpoint("/swagger/v1/swagger.json", "Dynoris API V1");
            });
            app.UseMvc();
        }

        public static IServiceProvider ConfigureDynorisServices(IConfigurationRoot configuration, IServiceCollection services)
        {
            services.AddSingleton<IConfiguration>(configuration);
            services.AddLogging();

            services.AddSwaggerGen(c =>
            {
                c.SwaggerDoc("v1", new Info { Title = "Dynoris API", Version = "v1" });
            });

            var awsOptions = configuration.GetAWSOptions();
            AWSConfigs.LoggingConfig.LogTo = LoggingOptions.Console;
            AWSConfigsDynamoDB.Context.TableNamePrefix = configuration
                .GetSection("aws")?
                .GetSection("dynamoDB")?
                .GetSection("dynamoDBContext")?["tableNamePrefix"];

            services.AddDefaultAWSOptions(awsOptions);
            services.AddAWSService<IAmazonDynamoDB>();

            // Add framework services.
            services.AddSingleton<IRedisConnectionFactory, RedisConnectionFactory>();

            services.AddScoped<IRedisServiceRecordProvider, RedisServiceRecordProvider>();
            services.AddScoped<IDynamoRedisProvider, DynamoRedisProvider>();
            services.AddScoped<IDynamoExpiringStampProvider, DynamoExpiringStampProvider>();

            return services.BuildServiceProvider();
        }
    }
}
