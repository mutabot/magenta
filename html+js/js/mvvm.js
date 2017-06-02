function AccountOptions(data) {
    this.album_links = ko.observable(data.album_links ? true : false);
    this.album_ignore_stamp = ko.observable(data.album_ignore_stamp ? true : false);
    this.time_space_min = ko.observable(data.time_space_min);
    this.in_cty = ko.observable(data.in_cty ? true : false);
}

function FilterInfo(data) {
    this.tagline = ko.observable(data.tagline);
    this.likes = ko.observable(data.likes);
    this.keyword = ko.observable(data.keyword);
    this.strip = ko.observable(data.strip ? true : false);
}

function LinkInfo(item, src) {
    var self = this;
    self.src = src.a;
    self.a = ko.observable(new AccountInfo(item.a, item.p));
    self.filter = ko.observable(new FilterInfo(src.filter));
    self.options = ko.observable(new AccountOptions(item.op));
    self.schedule = ko.observable(new Schedule(src.sch));
    self.uid = item.l.replace(/[^a-zA-Z0-9-_]/g, '') + src.a.id;

    // init method, called after KO render
    self.initSchedule = function () {
        self.schedule().init(self.uid);
    };

    // custom serializer is required due to schedule object complexity
    self.toJS = function () {
        return {
            l: { s: self.src.id, p: self.a().brand, id: self.a().id },
            f: self.filter(),
            sch: self.schedule().data,
            o: self.options()
        }
    }
}

function SyncSettingsInfo() {
    var self = this;
    self.checked = ko.observableArray(['keyword','tagline']);
}

function DashboardViewModel(onRefresh, api, user, dt_name) {
    // Data
    var self = this;

    self.dt = undefined;
    self.onRefresh = onRefresh;
    self.api = api;
    self.user = user;
    self.sources = ko.observableArray([]).extend({ rateLimit: 50 });  // AccountInfo
    self.providers = ko.observableArray([]);    // { p : name, i: ko.observableArray([AccountInfo]) }
    self.accountCount = ko.computed(function () {
        var count = 0;
        $.each(self.providers(), function (idx, p) {
            count += p.i().length;
        });
        return count;
    });
    self.linkCount = function () {
        return self.dt ? self.dt.otable.data().length : 0;
    };
    self.toggleSelectAllLinks = function () {
        if (self.dt) self.dt.toggleSelectAll();
    };
    self.clearSelectAllLinks = function () {
        if (self.dt) self.dt.selectAll(true);
    }
    self.toggleSelectAllLinksEx = function () {
        if (self.dt) self.dt.selectAll();
    }
   
    // Modal support
    self.sourceSelector = ko.observableArray([]);
    self.radioSelector = ko.observable();

    // Add provider modal
    self.addingProvider = ko.observable();
    self.addingProviderLink = ko.observable();
    self.addingProviderWarning = ko.observable();
    self.addingProviderValidation = ko.observable();
    self.addingProviderText = ko.observable('');
    self.addingProviderText.subscribe(function (value) {
        var re = new RegExp("^[0-9,]+$");    
        self.addingProviderValidation(value && re.test(value) ? undefined : 'Group IDs must be a list of numbers separated by commas!');        
    });
    self.addingProviderClick = function () {
        var t = self.addingProviderText();
        window.location.replace(self.addingProviderLink() + (t.length ? ('?t=' + t) : ''));
    };
    
    // account selector modal
    self.actionAccountInfo = ko.observable(); // AccountInfo

    // operation in progress?
    self.inProgress = ko.observable(false);

    // Operations
    self.addSourcePersonal = function (model, event) {
        self.addingProvider("Google Plus");
        self.addingProviderLink("/a/gl/login?personal");
        $('#addSourceModal').modal('show');
    }

    self.addSourcePage = function (model, event) {
        self.addingProvider("Google Plus");
        self.addingProviderLink("/a/gl/login?page");
        $('#addSourceModal').modal('show');
    }

    self.checkLimits = function (overLimitOnly) {
        return (self.user.checkTargetLimit(self.accountCount() + (overLimitOnly ? -1 : 0)));
    }

    self.addAccount1 = function (dst, destination) {
        localStorage.removeItem("renew-token");
        if (self.checkLimits(false)) {
            ga('send', 'event', 'event', 'target-add', destination);
            self.addingProvider(destination);
            self.addingProviderLink("/a/" + dst + "/login");
            self.addingProviderWarning(dst);
            $('#addAccModal').modal('show');
        }
    }

    self.refreshToken = function (dst, destination) {
        if (self.checkLimits(true)) {
            localStorage.setItem("renew-token", true);
            self.addingProvider(destination);
            self.addingProviderLink("/a/" + dst + "/login");
            $('#refreshAccModal').modal('show');
        }
    }
    
    self.addTargetToTree = function (item) {
        var ps = self.providers();
        for (var i = 0, j = ps.length; i < j; i++) {
            if (ps[i].p == item.p) {
                ps[i].i.push(new AccountInfo(item.a, item.p));
                return;
            }
        }
        self.providers.push({ p: item.p, i: ko.observableArray([new AccountInfo(item.a, item.p)]) });
    }
    // Get destination accounts
    self.getAccounts = function (onComplete) {
        self.api.viewGet('accounts', function (data) {
            self.providers.removeAll();
            $.each(data, function (idx, item) {
                self.addTargetToTree(item);
                $.each(item.src, function (idx, src) {
                    if (src.a) self.dt.otable.row.add({ a: item.a, p: item.p, l: item.l, op: item.op, s: src, li: new LinkInfo(item, src) });
                });
            });
            // sort accounts
            $.each(self.providers(), function (idx, item) { item.i.sort(function(a, b) { if (a.name < b.name) return -1; return 1; }) });

            self.providers.sort(function (a, b) {
                if (a.p < b.p)
                    return -1;
                if (a.p > b.p)
                    return 1;
            });
            self.dt.otable.draw();
            if (onComplete) onComplete();
        });
    }

    self.linkSettings = ko.observable(new LinkInfo(
        { a: { name: "", url: "", picture_url: "", master: true, id: "" }, p: "", l: "", op: { album_links: false, album_ignore_stamp: false, in_cty: false } },
        { a: { url: "", picture_url: "", id: "", name: "" }, filter: { tagline: null, likes: null, keyword: null, strip: null }, sch: null }));

    self.openSettings = function (data) {
        self.linkSettings(data.li);
        self.linkSettingsHTML(self.dt.getLinkHTML(data.li.uid));
        $('#linkSettings').modal('show');
    }

    // Get source accounts
    self.getSources = function (onComplete) {
        self.api.viewGet('sources', function (data) {
            self.sources($.map(data.filter(function (val) { return val != null; }), function (item) { return new AccountInfo(item); }));
            if (onComplete) onComplete();
        });
    }

    self.forgetAccount = function () {
        // removes the account and unlinks all sources
        var info = self.actionAccountInfo();
        if (info) {
            self.api.accountRemove({ p: info.brand, id: info.id }, function () {
                self.refresh();
                $.smallBox({
                    title: "<i class='fa fa-check txt-color-orangeDark'></i> Success <span class='txt-color-orangeDark'></span>",
                    content: "Account removed.",
                    color: "#296191",
                    iconSmall: "fa fa-thumbs-up bounce animated",
                    timeout: 4000
                });
            });
        } else {
            $.SmartMessageBox({
                title: "<i class='fa fa-check txt-color-orangeDark'></i> Info <span class='txt-color-orangeDark'></span>",
                content: "Something is not right. Please reload this browser window.",
                buttons: "[OK]"
            }, function (buttonPressed) {
                self.refresh();
            });
        }
    }
    self.linkAccountsToggle = function () {
        $.each(self.sources(), function (idx, itm) {
            var uid = itm.id;
            if (self.sourceSelector.indexOf(uid) == -1) {
                self.sourceSelector.push(uid);
            } else {
                self.sourceSelector.remove(uid);
            }
        });        
    }

    self.beginLinkAccounts = function (targetAccountInfo) {
        if (self.checkLimits(true)) {
            // cache this account info
            var sources = $.map(self.sources(), function (item) { return item.id; })
            // autoselect all sources if less than 5
            if (sources && sources.length < 5) {
                self.sourceSelector(sources);
            } 
            self.actionAccountInfo(targetAccountInfo);
            $('#linkAccModal').modal('show');
        }
    }

    self.linkAccounts = function () {
        var selected = self.sourceSelector();
        var account = self.actionAccountInfo();
        if (account && selected.length) {
            var links = [];
            var i;
            for (j = 0; j < selected.length; ++j) {
                links.push({ s: { id: selected[j] }, d: { p: account.brand, id: account.id } });
            }

            self.api.accountLink(links, function (data) {
                self.refresh();
                $.smallBox({
                    title: "<i class='fa fa-check txt-color-orangeDark'></i> Success <span class='txt-color-orangeDark'></span>",
                    content: selected.length + " account(s) are linked to the target!<br />You can now proceed to sharing new content. Or use 'Settings...' button to access crosspost options.",
                    color: "#296191",
                    iconSmall: "fa fa-thumbs-up bounce animated",
                    timeout: 10000
                });
            });
        } else {
            $.SmartMessageBox({
                title: "<i class='fa fa-check txt-color-orangeDark'></i> Warning <span class='txt-color-orangeDark'></span>",
                content: "No accounts selected to be linked. <br />Set slider next to account to 'ADD' to add the account to selection.",
                buttons: "[OK]"
            });
        }
    }

    self.unlinkAccount = function (data) {
        var links = [{ s: { id: data.l.s }, d: { p: data.l.p, id: data.l.id } }];
        self.api.accountUnlink(links, function (data) {
            self.refresh();
            $.smallBox({
                title: "<i class='fa fa-check txt-color-orangeDark'></i> Success <span class='txt-color-orangeDark'></span>",
                content: "Accounts unlinked.",
                color: "#296191",
                iconSmall: "fa fa-thumbs-up bounce animated",
                timeout: 10000
            });
        });
    }

    self.saveLinkSettings = function (data) {
        self.api.accountSave(data, function (data) {
            $.smallBox({
                title: "Success",
                content: "<i class='fa fa-check'></i> <i>Link options updated</i>",
                color: "#296191",
                iconSmall: "fa fa-thumbs-up bounce animated",
                timeout: 4000
            });
        });
    }

    self.forgetAccountEx = function (a, b) {
        self.actionAccountInfo(a);
        // show dialog
        $('#forgetAccModal').modal('show');
    }

    self.pokeSource = function (info) {
        self.api.sourcePoke({ id: info.id }, function (data) {
            $.smallBox({
                title: "Success",
                content: "<i class='fa fa-check'></i> <i>Source <strong>" + info.name + "</strong> (" + info.id + ") is being updated...</i>",
                color: "#296191",
                iconSmall: "fa fa-thumbs-up bounce animated",
                timeout: 4000
            });
        });
    }

    self.forgetSource = function (info) {
        self.actionAccountInfo(info);
        $('#forgetSourceModal').modal('show');
    }   

    self.forgetSourceConfirm = function () {
        var info = self.actionAccountInfo();
        self.api.sourceForget({ id: info.id }, function (data) {
            self.refresh();
            $.smallBox({
                title: "Success",
                content: "<i class='fa fa-check'></i> <i>Source <strong>" + info.name + "</strong> (" + info.id + ") is forgotten...</i>",
                color: "#296191",
                iconSmall: "fa fa-thumbs-up bounce animated",
                timeout: 4000
            });
        });
    }

    self.cloneSource = function (info) {
        self.actionAccountInfo(info);
        self.radioSelector(null);
        $('#cloneSourceModal').modal('show');
    }

    self.cloneSourceConfirm = function () {
        var info = self.actionAccountInfo();
        var to = self.radioSelector();
        self.api.sourceClone({ src_gid: info.id, tgt_gid: to }, function (data) {
            self.refresh();
            $.smallBox({
                title: "Success",
                content: "<i class='fa fa-check'></i> <i>Source links from <strong>" + info.name + "</strong> (" + info.id + ") copied ...</i>",
                color: "#296191",
                iconSmall: "fa fa-thumbs-up bounce animated",
                timeout: 4000
            });
        });
    }

    self.onUnlinkAccount = function (link) {
        $.SmartMessageBox({
            title: "<i class='fa fa-check txt-color-orangeDark'> </i>&nbsp; Unlinking Accounts <span class='txt-color-orangeDark'></span>",
            content: "<br /><p>Breaking link will disable posting to the target account.</p><p>Current link settings will be preserved and will be in effect if this link is restored.</p><p><strong class='txt-color-red'>WARNING:</strong> Source posts shared while accounts are not linked <strong>cannot ever</strong> be processed.</p><br /><p>Are you sure you like to continue?</p><br />",
            buttons: "[Continue][Cancel]"
        }, function (btn) {
            if (btn == 'Continue') {
                self.unlinkAccount(ko.mapping.toJS(self.linkSettings().toJS()));
            }
        });
    }

    self.onSaveLinkSettings = function (link) {
        self.saveLinkSettings(ko.mapping.toJS(self.linkSettings().toJS()));
    }

    self.refreshStack = [];
    self.refreshComplete = function () {
        self.refreshStack.pop();
        if (self.refreshStack.length == 0) {
            $('#loading-cog').hide();
            if (self.accountCount() == 0) {
                setTimeout(function () { $('#add-target-help').show(); }, 3000);
            } else if (self.linkCount() == 0) {
                setTimeout(function () {
                    if (self.linkCount() == 0 && $('#linkAccModal:visible').length == 0) {
                        $.smallBox({
                            title: "<i class='fa fa-info txt-color-white'></i> &nbsp;Hint!",
                            content: "<h4>Link targets to source(s) by clicking 'Link to Source' buttons in Target Account settings.<h4><br /><p>Once link is created, link settings will be available via <kbd class='font-md'><i class='fa fa-fw fa-sliders'></i></kbd> buttons in the 'Account Links' section.</p><br />",
                            color: "#296191",
                            iconSmall: "fa fa-thumbs-up bounce animated",
                            timeout: 60000
                        });
                    }
                }, 10000);
            }
            if (self.onRefresh) self.onRefresh();
        }
    }

    self.syncSettings = ko.observable(new SyncSettingsInfo());
    self.syncSetingsSelected = [];
    self.linkSettingsHTML = ko.observable("");
    self.syncSettingsCount = ko.observable(0);
    self.populateChecked = function () {
        self.syncSetingsSelected = $.map(self.dt.getChecked(), function (item) {
            return ko.mapping.toJS($.extend({}, item.li.toJS().l, { 'uid': item.li.uid }));
        });
    }

    self.openSyncSettingsModal = function () {        
        self.populateChecked();
        if (self.syncSetingsSelected.length <= 0) {
            $.smallBox({
                title: "Please select multiple links to apply settings cloning",
                content: "Settings will be cloned from the highlighted template link to the rest of the links from the selection.",
                color: "#900323",
                iconSmall: "fa fa-info bounce animated",
                timeout: 20000
            });
            return;
        }
        if (self.syncSetingsSelected.length == 1) {
            self.dt.selectAll();
            self.populateChecked();
        }
        self.linkSettingsHTML(self.dt.getLinkHTML(self.syncSetingsSelected[0].uid));
        self.syncSettingsCount(self.syncSetingsSelected.length - 1);
        $('#syncSettingsModal').modal('show');
    }

    self.applySyncSettings = function () {
        var src = self.syncSetingsSelected.splice(0, 1);
        var post_data = {
            'ref': src[0],
            'tgt': self.syncSetingsSelected.splice(0, self.syncSetingsSelected.length),
            'in' : self.syncSettings().checked()
        }
        self.api.accountSync(ko.mapping.toJS(post_data), function (data) {
            $.smallBox({
                title: "Success",
                content: "<i class='fa fa-check'></i> <i>Link settings synchronized</i>",
                color: "#296191",
                iconSmall: "fa fa-thumbs-up bounce animated",
                timeout: 4000
            });
            self.refresh();
        });
    }

    // pull account data
    self.refresh = function () {
        if (!self.dt) {
            self.dt = new LinksDataTable(dt_name, self.openSettings, self.openSync);
        } else {
            self.dt.clear();
        }
        self.refreshStack.push(1, 2);
        self.getSources(self.refreshComplete);
        self.getAccounts(self.refreshComplete);
    }

    self.reset = function () {
        self.providers([]);
        $('#loading-cog').show();
        self.getAccounts(self.refreshComplete);
    }
}
