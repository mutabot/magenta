function AccountInfo(data, brand) {
    this.brand = brand ? brand : '';
    this.id = data.id;
    this.name = data.name;
    this.url = data.url;
    this.picture_url = data.picture_url ? data.picture_url : '/img/profile.png';
}

function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.hash);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function LogItem(gid, stamp, message) {
    var self = this;
    self.gid = gid;
    self.stamp = stamp;
    self.message = message;
    self.getLocalStamp = function () {
        return self.stamp.toLocaleTimeString();
    };
}

function LogDay(day, items) {
    var self = this;
    self.day = new Date(day);
    self.day.setHours(0, 0, 0, 0);

    self.items = items;
    self.getLocalStamp = function () {
        return self.day.toDateString();
    };
    self.sort = function () {
        self.items.sort(function (a, b) {
            return b.stamp - a.stamp;
        });
    };
}

function UserInfo(data) {
    var self = this;
    self.gid = data.gid;
    self.tnc = data.tnc;
    self.url = data.url;
    self.name = data.name;
    self.avatar_url = data.avatar_url;
    self.limits = data.limits;
}

function UserViewModel(api) {
    // Data
    var self = this;
    self.api = api;
    self.user = ko.observable(new UserInfo({ gid: '', tnc: '', url: '', name: '', avatar_url: '/img/avatar.png', limits: null }));
    self.tnc = ko.observable(false);
    self.email = ko.observable(true);
    self.confirm_remove = ko.observable(false);
    self.log = ko.observableArray([]);
    self.working = ko.observable(false);

    self.onWorking = function () {
        self.working(true);
    }

    self.onIdle = function () {
        self.working(false);
    }

    self.api.addWorkingHandler(self.onWorking);
    self.api.addIdleHandler(self.onIdle);
    self.onuser = [];

    self.checkUser = function (onRedirect) {
        // no user, push to notify cache
        if (self.user().gid.length == 0) {
            console.log('no user...');
            console.log(onRedirect);
            if (onRedirect) self.onuser.push(onRedirect);
            return false;
        } else if (onRedirect) {
            onRedirect();
        }
        return true;
    }
    self.checkRedirect = function () {
        if (self.onuser.length > 0) {
            console.log('Calling callback...')
            self.onuser.pop()();
        }
    }
    self.getUser = function (onComplete) {
        // Get User
        self.api.userGet('', function (data) {
            if (data && data.gid) {
                self.user(new UserInfo(data));
                self.tnc((data.tnc && data.tnc.tnc) ? true : false);
                if (!self.tnc()) {
                    // trap hash change
                    $(window).on('hashchange', function () {
                        if (!userModel.tnc() && window.location.hash != '#!/welcome.html' && $(".SmallBox").find('#terms-link').length == 0) {
                            $.smallBox({
                                title: "<i class='fa fa-bell' id='terms-link'></i> &nbsp; Warning!",
                                content: "<strong>Account is not active.</strong> <br />Please click on this box to go to activation page.",
                                color: "orange",
                                iconSmall: "fa fa-exclamation bounce animated",
                                timeout: 120000
                            }, function () {
                                window.location.hash = '#!/welcome.html';
                            });
                        }
                    });
                    // redirect to activation screen
                    window.location.hash = '#!/welcome.html';
                }
                else if (onComplete) {
                    onComplete();
                }
            } else {
                window.location = '/';
            }
        });
    }


    self.agreeTerms = function () {
        self.api.agreeTerms({ email: self.email() },
            function () {
                $.SmartMessageBox({
                    title: "<i class='fa fa-check txt-color-orangeDark'> </i>&nbsp; Success <span class='txt-color-orangeDark'></span>",
                    content: "Your account is now active.",
                    buttons: "[Continue]"
                }, function () {
                    window.location.hash = '#!/login.html';
                });
            });
    }

    self.updateInfo = function () {
        self.api.updateInfo({ email: self.email() },
            function () {
                $.smallBox({
                    title: "<i class='fa fa-check txt-color-orangeDark'></i> Success <span class='txt-color-orangeDark'></span>",
                    content: "Account settings updated.",
                    color: "#296191",
                    iconSmall: "fa fa-thumbs-up bounce animated",
                    timeout: 4000
                });
            });
    }

    self.deleteAccount = function () {
        self.api.deleteAccount({},
            function (data) {
                if (typeof (data) == typeof (true) && data == true) {
                    $.SmartMessageBox({
                        title: "<i class='fa fa-check txt-color-orangeDark'></i> Sorry to see you go! <span class='txt-color-orangeDark'></span>",
                        content: "Your account and any associated billing plans have been cancelled successfully.",
                        buttons: "[Continue]"
                    }, function () {
                        setTimeout(function () { window.location.replace('/'); }, 350);
                    });
                } else {
                    var msg = typeof (data) == typeof ({}) && "error" in data ? "<p>Server message</p><h3><strong>" + data["error"] + "</strong></h3>" : "";
                    $.SmartMessageBox({
                        title: "<i class='fa fa-fw fa-bug txt-color-red'></i> Something went wrong...! <span class='txt-color-orangeDark'></span>",
                        content: "<p>Errors occurred while communicating to our servers.</p> <p>Please contact support using contact methods listed in our Help.</p><br />" + msg,
                        buttons: "[Continue to Help]"
                    }, function () {
                        setTimeout(function () { window.location.hash = '#!/help.html?support'; }, 350);
                    });
                }
            });
    }
    self.getLog = function () {
        self.api.userGet('log', function (data) {
            var days = [];

            $.each(data, function (k, item) {
                $.each(item, function (idx, entry) {
                    var d = new Date();
                    d.setTime(entry[1] * 1000);
                    var myday = $.grep(days, function (day) {
                        return day.day.toDateString() == d.toDateString();
                    });
                    if (myday.length <= 0) {
                        day = new LogDay(d, [new LogItem(k, d, entry[0])]);
                        days.push(day);
                    }
                    else {
                        myday[0].items.push(new LogItem(k, d, entry[0]));
                    }
                });
            });
            $.each(days, function (idx, d) {
                d.sort();
            });
            self.log(days.sort(function (a, b) {
                return b.day.getTime() - a.day.getTime();
            }));
            $('.tree > ul').attr('role', 'tree').find('ul').attr('role', 'group');
            $('.tree').find('li:has(ul)').addClass('parent_li').attr('role', 'treeitem').find(' > span').attr('title', 'Collapse this branch').on('click', function (e) {
                var children = $(this).parent('li.parent_li').find(' > ul > li');
                if (children.is(':visible')) {
                    children.hide('fast');
                    $(this).attr('title', 'Expand this branch');
                } else {
                    children.show('fast');
                    $(this).attr('title', 'Collapse this branch');
                }
                e.stopPropagation();
            });
        });
    }

    self.getInfo = function () {
        self.confirm_remove(false);
        self.api.userGet('info', function (data) {
            self.email(data.info && data.info.email);
        });
    }

    self.checkTargetLimit = function (targetCount) {
        var tLimit = self.user().limits.target;
        if (self.user().limits && targetCount >= tLimit) {
            ga('send', 'event', 'event', 'limit', 'acc-target', targetCount);
            $.smallBox({
                title: "<strong class='fa fa-lg swing animated fa-circle-o-notch txt-color-red'></strong> &emsp; Limit Reached",
                content: "<p>You have reached your target account limit.<br />Reduce number of target accounts or upgrade to continue...</p><h3 class='text-align-center'>Ready for an upgrade?</h3> <p class='text-align-center'><a href='#!/order.html' id='btn-box-yes' class='btn btn-primary'>Yes</a> <a href='javascript:void(0);' class='btn btn-danger'>No</a></p><br /><p>Your target account limit is: <kbd>" + tLimit + "</kbd><p><i class='note txt-color-lighten'>Upgrading is easy and only takes a minute.<br />We accept PayPal and all major credit cards.</i>",
                color: "#5b835b",
                iconSmall: "fa fa-shopping-cart bounce animated",
                timeout: 60000
            });
            $("#btn-box-yes").click(function () { ga('send', 'event', 'button', 'click', 'limit-box-yes', tLimit); });
            return false;
        }
        return true;
    }

    self.bind = function (node) {
        ko.applyBindings(self, node);
        self.getInfo();
    }
}