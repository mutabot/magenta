using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authentication;
using System.Threading.Tasks;
using System.Linq;

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

        [HttpGet]
        public async Task SignedIn()
        {
            var context = HttpContext;
            // Setting DefaultAuthenticateScheme causes User to be set
            var user = context.User;

            // Deny anonymous request beyond this point.
            if (user == null || !user.Identities.Any(identity => identity.IsAuthenticated))
            {
                // This is what [Authorize] calls
                // The cookie middleware will intercept this 401 and redirect to /login
                await context.ChallengeAsync();

                // This is what [Authorize(ActiveAuthenticationSchemes = MicrosoftAccountDefaults.AuthenticationScheme)] calls
                // await context.ChallengeAsync(MicrosoftAccountDefaults.AuthenticationScheme);

                return;
            }
        }

    }
}