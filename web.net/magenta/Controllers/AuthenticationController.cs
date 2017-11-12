using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authentication;
using System.Threading.Tasks;

namespace magenta.Controllers
{
    [Produces("application/json")]
    [Route("/gl")]
    public class AuthenticationController : Controller
    {
        [HttpGet]
        [Route("login")]
        public IActionResult SignIn()
        {
            // Instruct the middleware corresponding to the requested external identity
            // provider to redirect the user agent to its own authorization endpoint.
            // Note: the authenticationScheme parameter must match the value configured in Startup.cs
            return Challenge(new AuthenticationProperties { RedirectUri = "https://local.irisriver.com/i.html#!/login.html" }, "Google");
        }

        [HttpGet]
        [Route("logout")]
        public async Task SignOut()
        {
            await HttpContext.SignOutAsync();
            Response.Redirect("https://local.irisriver.com");
        }
    }
}