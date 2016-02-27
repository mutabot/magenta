function OrderApi(onError, pace) {
    var self = this;
    self.onError = onError;
    self.orderGet = function (what, onComplete) {
        $.ajax({
            url: '/p/api/v1/order/' + what,
            dataType: 'json',
            cache: false,
            type: 'GET',
            data: '',
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }
    self.orderPost = function (what, data, onComplete) {
        $.ajax({
            url: '/p/api/v1/order/' + what,
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data)
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }
}
function OrderViewModel() {
    // Data
    var self = this;
    self.api = new OrderApi(function (errorCode) {       
            $.SmartMessageBox({
                title: "<i class='fa fa-sign-out txt-color-orangeDark'></i> ERROR: Failure while communicating to server... <span class='txt-color-orangeDark'></span>",
                content: "Please close this browser tab and try again.<br /> Contact support if this error persists.",
                buttons: "[Close]"
            });
    });

    self.allPlans = ko.observableArray([]);
    self.selectedPlan = ko.observable();
    self.log = ko.observableArray([]);
    self.working = ko.observable(true);
    self.selectedPlanRead = ko.computed(function () {
        return self.selectedPlan() ? self.selectedPlan() : { name: '', price: 0.0, description: '', ccy: '' };
    });

    self.onPlanSelect = function (obj, event) {
        self.plan(obj);
    };

    self.orderSubscribe = function (plan, nonce) {
        self.working(true);
        var dd = $('#checkout #device_data').val();
        self.api.orderPost("subscribe",
            { plan: plan, nonce: nonce, dd: dd },
            function (data) {
                self.working(false);
                if (data.error && data.error.length > 0) {
                    self.processError(data);
                } else {
                    $.SmartMessageBox({
                        title: "<i class='fa fa-heart txt-color-white'> </i>&nbsp; Success!",
                        content: "<br /><h1>Your payment has been accepted.</h1><h3 class='txt-color-green'>Thank you for using our service!</h3>",
                        buttons: "[Continue]"
                    }, function () {
                        ga('send', 'event', 'event', 'order', 'complete');
                        userModel.getUser(function () {
                            window.location.hash = '#!/billing.html';
                        });
                    });
                }
            });
    };
    self.cancelPlan = function () {
        $.SmartMessageBox({
            title: "Are you sure you like to cancel the subscription<i class='fa fa-question txt-color-orangeDark'></i>",
            content: "<p>Cancelling subscription will stop all billing on your account.</p><p>Your plan will be downgraded to 'Free Plan' and the account will remain active.</p><br /><h3>Press \"Yes\" to proceed and cancel the subscription or \"No\" to return to previous sceen.</h3><p class='note'><strong>To completely delete your account proceed to <a href='#!/account.html'>My Account->Settings</a> page.<strong></p>",
            buttons: "[No][Yes]"
        }, function (btn) {
            if (btn != "Yes") {
                return;
            };
            self.working(true);
            self.api.orderPost("cancel",
                {},
                function (data) {
                    self.working(false);
                    if (data.error && data.error.length > 0) {
                        self.processError(data);
                    } else {
                        $.SmartMessageBox({
                            title: "<i class='fa fa-check txt-color-orangeDark'></i> Success!",
                            content: "<p>The subscription has been cancelled. You can continue using the service in trial mode.</p></p>Feel free to let us know what can be improved about the service.</p><p><a href='/page.html#!/about.html'>Click here to contact us</a></p>",
                            buttons: "[Continue]"
                        }, function () {
                            ga('send', 'event', 'event', 'order', 'canceled');
                            window.location.reload();
                        });
                    }
                });
        });
    };
    self.upgradePlan = function () {
        $.SmartMessageBox({
            title: "<i class='fa fa-heart txt-color-white'> </i> &nbsp;Thank you for choosing our service!",
            content: "<br /><h3>Click \"Continue\" to get redirected to our ordering page.</h3><h4><strong class='txt-color-green'>Your current plan will be cancelled automatically during re-subsciption.</strong></h4>",
            buttons: "[Continue]"
        }, function (btn) {
            setTimeout(function () { window.location.hash = '#!/order.html'; }, 100);
            ga('send', 'event', 'event', 'order', 'upgrade');
        });
    };
    self.setupOrder = function (OnComplete) {
        self.api.orderGet("token",
            function (data) {
                BraintreeData.setup(data.m, "checkout", data.e == "P" ? BraintreeData.environments.production : BraintreeData.environments.sandbox);
                braintree.setup(data.t, "dropin",
                    {
                        container: "checkout",
                        paymentMethodNonceReceived: function (event, nonce) {
                            self.orderSubscribe(self.selectedPlanRead().id, nonce)
                        }
                    });

                if (OnComplete)
                    OnComplete();
            });
    };

    self.refresh = function (OnComplete) {
        self.api.orderGet("info",
            function (data) {
                if (data.error && data.error.length > 0) {
                    self.processError(data);
                } else {                    
                    var mappedPlans = data.plans;
                    mappedPlans.sort(function (a, b) { return parseFloat(a.price) - parseFloat(b.price); });                    
                    self.allPlans(mappedPlans);
                    var current = $.grep(mappedPlans, function (plan) { return data.p == plan.id; });
                    self.selectedPlan(current.length > 0 ? current[0] : { name: 'FREE', price: 0.0, description: '', ccy: '' });
                };
                self.working(false);
                if (OnComplete)
                    OnComplete();
            });
    };

    self.setDefaultPlan = function () {
        id = localStorage.getItem("magenta_plan");
        if (id && id.length) {
            for (i = 0; i < self.allPlans().length; i++) {
                if (self.allPlans()[i].id == id) {
                    self.selectedPlan(self.allPlans()[i]);
                    return;
                }
            }
        }
        self.selectedPlan(self.allPlans()[0]);
    };

    self.getHistory = function (OnComplete) {
        self.api.orderGet("history",
            function (data) {
                if (data.error && data.error.length > 0) {
                    self.processError(data);
                } else {
                    var mappedLog = $.map(data.h,
                        function (item) {
                            return {
                                t: new Date(parseFloat(item.t) * 1000.0),
                                m: item.m
                            };
                        });
                    self.log(mappedLog);
                }
            });
    };

    self.processError = function (data) {
        $.SmartMessageBox({
            title: "<i class='fa fa-bug txt-color-orangeDark'></i> Order was not submitted",
            content: "<br /><h3>" + data.error + "</h3><br /> Please try again later. Contact support if this error persists.",
            buttons: "[Close]"
        },
        function (a) {
            setTimeout(function () { window.location.replace("/page.html#!/plans.html"); }, 350);
        });
    };
}