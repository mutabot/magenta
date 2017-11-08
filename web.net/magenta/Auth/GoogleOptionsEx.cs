using Microsoft.AspNetCore.Authentication.Google;
using Microsoft.AspNetCore.Authentication.OAuth;
using Microsoft.AspNetCore.Http;
using System;

namespace magenta.Auth
{
    public class GoogleOptionsEx : GoogleOptions
    {
        /// <summary>
        /// Initializes a new <see cref="GoogleOptionsEx"/>.
        /// </summary>
        public GoogleOptionsEx() : base() { }

        public Uri CallbackUri { get; set; }
    }
}
