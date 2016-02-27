function AccountBag(data) {
    var self = this;

    self.info = new AccountInfo(data.a);
    self.brand = data.p;
    self.info.brand = data.p;
    self.icon = ko.computed(function () {
        if (self.brand == '500px') {
            return 'fa-500px';
        }
        return 'fa-' + self.brand;
    }, this);

    // Selector
    self.checked = ko.observable(true);
}

function SelectorViewModel(api) {
    // Data
    var self = this;

    self.api = api;
    self.working = ko.observable(false);

    self.sources = ko.observableArray([]);
    self.allNoneSrc = ko.observable(true);
    self.allNoneSrc.subscribe(function () {
        $.each(self.sources(), function (idx, itm) {
            itm.checked(!itm.checked());
        });
    });

    self.accounts = ko.observableArray([]);
    self.allNoneTgt = ko.observable(true);
    self.allNoneTgt.subscribe(function () {
        $.each(self.accounts(), function (idx, itm) {
            itm.checked(!itm.checked());
        });
    });    

    self.onWorking = function () {
        self.working(true);
    }

    self.onIdle = function () {
        self.working(false);
    }

    self.api.addWorkingHandler(self.onWorking);
    self.api.addIdleHandler(self.onIdle);

    self.isRefresh = function () {
        return localStorage.getItem("renew-token") ? true : false;
    }

    // Operations
    // Get unlinked accounts
    self.getAccounts = function (onComplete) {
        self.api.viewSelector(function (data) {            
            self.accounts($.map(data.sel, function (item) { return new AccountBag(item) }));
            self.sources($.map(data.src, function (item) {
                return new AccountBag({
                    a: { id: item.id, name: item.name, url: item.link, picture_url: item.picture },
                    p: 'google'
                });
            }));
            onComplete();
        },
        localStorage.getItem("renew-token") ? 'refresh' : '');
    }

    self.cancelSelection = function () {
        window.location.hash = '#!/dashboard.html';
    }

    self.addAccounts = function () {
        var tgt_data = [];
        var src_data = [];
        $.each(self.accounts(), function (idx, acc) {
            if (!acc.checked()) return;
            tgt_data.push({ p: acc.brand, id: acc.info.id });            
        });
        $.each(self.sources(), function (idx, acc) {
            if (!acc.checked()) return;
            src_data.push({ p: acc.brand, id: acc.info.id });
        });
        
        var plr = (tgt_data.length > 1);
        var msg = tgt_data.length + " account" + (plr ? "s" : "") + " authenticated."

        if (tgt_data.length > 0) {
            self.api.accountAdd({ tgt: tgt_data, src: src_data }, function (result) {
                if (result) {
                    $.SmartMessageBox({
                        title: "<i class='fa fa-check txt-color-orangeDark'></i> Success <span class='txt-color-orangeDark'></span>",
                        content: msg,
                        buttons: "[Continue to Dashboard]"
                    }, function (a) {
                        ga('send', 'event', 'event', 'target-added', 'target-count', tgt_data.length);
                        setTimeout(function () { window.location.hash = '#!/dashboard.html'; }, 350);
                    });
                }
                else {
                    $.SmartMessageBox({
                        title: "<i class='fa fa-asterisk txt-color-orangeDark'></i> Warning ",
                        content: "Failed to add account(s). Please retry your request.<br />Contact support if this error persists.",
                        buttons: "[Continue to Dashboard]"
                    }, function (a) {
                        setTimeout(function () { window.location.hash = '#!/dashboard.html'; }, 350);
                    });
                }
            });
        } else {
            if (self.accounts().length > 0) {
                $.SmartMessageBox({
                    title: "<i class='fa fa-check txt-color-orangeDark'></i> Info <span class='txt-color-orangeDark'></span>",
                    content: "You have not selected any accounts to add. Continue to Dashboard?",
                    buttons: "[Select Accounts][Continue to Dashboard]"
                }, function (buttonPressed) {
                    if (buttonPressed == "Continue to Dashboard") {
                        setTimeout(function () { window.location.hash = '#!/dashboard.html'; }, 350);
                    }
                });
            } else {
                window.location.hash = '#!/dashboard.html';
            }
        }
    };

    self.refresh = function (onComplete) {
        self.getAccounts(onComplete);
    }
}