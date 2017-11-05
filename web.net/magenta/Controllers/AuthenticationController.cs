using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authentication;

namespace magenta.Controllers
{
    [Produces("application/json")]
    [Route("/gl/login")]
    public class AuthenticationController : Controller
    {
        [HttpGet]
        public IActionResult SignIn()
        {
            // Instruct the middleware corresponding to the requested external identity
            // provider to redirect the user agent to its own authorization endpoint.
            // Note: the authenticationScheme parameter must match the value configured in Startup.cs
            return Challenge(new AuthenticationProperties { RedirectUri = "https://irisriver.com/a/gl/login" }, "Google");
        }
    }
}