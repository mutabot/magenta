function MagentaModelBag() {
    var self = this;    
    self.magentaApi = new MagentaApi(function (errorCode) {
        if (errorCode == 401) {
            $.SmartMessageBox({
                title: "<i class='fa fa-sign-in txt-color-orangeDark'></i> Please sign in to continue... <span class='txt-color-orangeDark'></span>",
                content: "<br />Click a sign in provider button below to sign in.<br />New users will be asked to create an account.<br /><button class='botTempo' id='bot1-Msg1' style='background-color: rgba(0, 0, 0, 0);border: 0;margin-top: 15pt;'><img src='/img/google/1x/btn_google_signin_dark_normal_web.png' /></button>",
                buttons: "foo"
            }, function (a) {              
                if (window.location.hash != '#!/login.html') localStorage.setItem("magenta_redirect", window.location.hash);
                window.location.replace('/a/gl/login?clear');
            });
        }
        else {
            $.SmartMessageBox({
                title: "<i class='fa fa-sign-out txt-color-orangeDark'></i> Failure while communicating to server... <span class='txt-color-orangeDark'></span>",
                content: "Please refresh this browser tab and try again.<br /> Contact support if this error persists.",
                buttons: "[Continue]"
            }, function (a) {
                window.location.reload();
            });
        }
    });

    self.userModel = new UserViewModel(self.magentaApi);
    console.log('user model created');
    // apply bindings 
    ko.applyBindings(self.userModel, document.getElementById("header"));
    ko.applyBindings(self.userModel, document.getElementById("left-panel"));
    ko.applyBindings(self.userModel, document.getElementById("shortcut"));
    ko.applyBindings(self.userModel, document.getElementById("ribbon"));

    // refresh user data
    self.userModel.getUser(function () {
        if (self.userModel.checkUser()) {
            // redirect back to where we took off from
            var r = localStorage.getItem("magenta_redirect");
            localStorage.removeItem("magenta_redirect");
            if (r && r.length > 0 && r != window.location.hash) {
                console.log('magenta_redirect to ' + r);
                window.location.hash = r;
            } else {
                console.log('check redirect');
                self.userModel.checkRedirect();
            }
        } else {
            $.SmartMessageBox({
                title: "<i class='fa fa-sign-out txt-color-orangeDark'></i> Something went wrong... <span class='txt-color-orangeDark'></span>",
                content: "<p>Could not retrieve user data from server.</p><p>Please let us know about this problem. <a href='/page.html#!/help.html?support'>Click here</a> for contact options.</p>",
                buttons: "[Retry Login]"
            }, function (a) {
                window.location.replace('/a/gl/login?clear');
            });
        }
    });
}