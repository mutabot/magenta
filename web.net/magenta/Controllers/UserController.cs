using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;

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

            return new
            {
                gid = "gid",
                tnc = "tnc",
                name = "name",
                url = "url",
                avatar_url = "picture_url",
                limits = "limits"
            };
        }

        // POST: api/User
        [HttpPost]
        public void Post([FromBody]string value)
        {
        }
    }
}
