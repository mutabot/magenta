using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Authentication;
using System.Threading.Tasks;
using System.Net;
using Microsoft.Extensions.Logging;
using System.Linq;
using System.Collections.Generic;
using System;

namespace magenta
{
    public class Startup
    {
        private readonly Dictionary<string, string> Redirects;
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
            Redirects = Configuration.GetSection("Redirects")
                .GetChildren()
                .ToDictionary(c => c.Key, c => c.Value);
        }

        public IConfiguration Configuration { get; }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            services.AddLogging();
            services.AddMvc();

            services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
                .AddCookie(o =>
                {
                    o.Cookie.Name = "magenta_session";
                })
                .AddGoogle(o =>
                {
                    o.ClientId = "985571252367-9al6vae83ldbt700tru23k25ta878n4o.apps.googleusercontent.com";
                    o.ClientSecret = "CiY5mPfj4qfzWGxaqSo-gAjp";
                });
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, ILoggerFactory loggerFactory)
        {
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }

            app.UseAuthentication();

            app.UseMvc();
        }
    }
}
