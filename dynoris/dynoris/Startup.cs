using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Amazon.DynamoDBv2;
using Amazon.Extensions.NETCore.Setup;
using dynoris.Providers;

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
            // register dependencies
            services.AddLogging();
            services.AddSingleton<IConfiguration>(Configuration);            
            var awsOptions = Configuration.GetAWSOptions();
            Amazon.AWSConfigs.LoggingConfig.LogTo = Amazon.LoggingOptions.Console;

            services.AddDefaultAWSOptions(awsOptions);
            services.AddAWSService<IAmazonDynamoDB>();

            services.AddSingleton<RedisServiceRecordProvider>();

            // Add framework services.
            services.AddMvc();
            services.AddSingleton<IDynamoRedisProvider, DynamoRedisProvider>();
            services.AddSingleton<IConfiguration>(Configuration);
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, ILoggerFactory loggerFactory)
        {
            loggerFactory.AddConsole(Configuration.GetSection("Logging"));
            loggerFactory.AddDebug();
            loggerFactory.AddFile(Configuration.GetSection("Logging"));

            app.UseMvc();
        }
    }
}
