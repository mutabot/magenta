using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.Extensions.Logging;
using System.Linq;
using System.Collections.Generic;
using Microsoft.AspNetCore.Authentication.Google;
using Microsoft.AspNetCore.Authentication;
using magenta.Auth;
using Microsoft.AspNetCore.Http;
using System;
using Microsoft.AspNetCore.Authentication.OAuth.Claims;
using Newtonsoft.Json.Linq;
using System.Security.Claims;

namespace magenta
{
    public class GoogleClaimsAction : ClaimAction
    {
        public GoogleClaimsAction(string claimType, string valueType) : base(claimType, valueType)
        {
        }

        public override void Run(JObject userData, ClaimsIdentity identity, string issuer)
        {

            var infoJson = new JObject(
                new JProperty("family_name", userData.SelectToken("name.familyName")),
                new JProperty("name", userData.SelectToken("displayName")),
                new JProperty("picture", userData.SelectToken("image.url")),
                new JProperty("email", userData.SelectToken("$.emails[?(@.type == 'account')].value")),
                new JProperty("link", userData.SelectToken("url")),
                new JProperty("given_name", userData.SelectToken("name.givenName")),
                new JProperty("id", userData.SelectToken("id"))
                );
            //            {
            //                "family_name": "Shmalko",
            //   "name":  "Michael Shmalko",
            //   "picture":  "https://lh6.googleusercontent.com/-AELM2ft_rbM/AAAAAAAAAAI/AAAAAAAADJw/v3YTWJVPi_Y/photo.jpg",
            //   "locale":  "en",
            //   "gender":  "male",
            //   "email":  "mshmalko@gmail.com",
            //   "link":  "https://plus.google.com/+\u041c\u0438\u0445\u0430\u0439\u043b\u043e\u0407\u0436\u0454\u043c\u0430\u0456",
            //   "given_name":  "Michael",
            //   "id":  "111780410677417445421",
            //   "verified_email":  true
            //}
            //        }

            var claim = new Claim("user:info", infoJson.ToString());
            identity.AddClaim(claim);
        }
    }

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
                // .AddJwtBearer
                .AddCookie(o =>
                {
                    o.Cookie.Name = "magenta_session";
                })
                .AddOAuth<GoogleOptionsEx, GoogleHandlerEx>(GoogleDefaults.AuthenticationScheme, GoogleDefaults.DisplayName, o =>
                {
                    o.CorrelationCookie = new CookieBuilder
                    {
                        HttpOnly = false,
                        SecurePolicy = CookieSecurePolicy.SameAsRequest
                    };
                    o.SaveTokens = true;
                    o.CallbackUri = new Uri("https://local.irisriver.com/a/gl");
                    o.CallbackPath = "/gl";
                    o.ClientId = "985571252367-9al6vae83ldbt700tru23k25ta878n4o.apps.googleusercontent.com";
                    o.ClientSecret = "CiY5mPfj4qfzWGxaqSo-gAjp";
                    o.ClaimActions.MapJsonSubKey("urn:google:image", "image", "url");
                    o.ClaimActions.Add(new GoogleClaimsAction("all", "json"));
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
