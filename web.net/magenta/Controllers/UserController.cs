using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Newtonsoft.Json.Linq;
using System.IO;

namespace magenta.Controllers
{
    [Produces("application/json")]
    [Route("/api/v1/user")]
    [Authorize]
    public class UserController : Controller
    {
        [HttpGet]
        public async Task<dynamic> Get()
        {
            var user = HttpContext.User;
            var userInfo = JObject.Parse(user.Claims.First(c => c.Type == "user:info").Value);

            return new
            {
                gid = userInfo["id"],
                tnc = "tnc",
                name = userInfo["name"],
                url = userInfo["link"],
                avatar_url = userInfo["picture"],
                limits = "limits"
            };
        }

        // POST: api/User
        [HttpPost]
        [Route("agree")]
        public bool Agree([FromBody]JObject value)
        {
            var emailConsent = value.SelectToken("email");

            return true;
        }
    }
}
