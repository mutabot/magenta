function ServiceApi(onError) {
    var self = this;
    self.onError = onError;
    self.serviceGet = function (onComplete) {
        $.ajax({
            url: '/a/api/v1/service',
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
    self.serviceAsUser = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/service/as_user',
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

function PollerStats(data) {
    var self = this;
    self.name = data.name;
    self.day = data.day;
    self.hour = data.hour;
}

function ServiceViewModel() {
    // Data
    var self = this;

    self.api = new ServiceApi(function (errorCode) {
        if (errorCode == 401) {
            // No op -- user model should pick up all auth issues
        }
        else {
            $.SmartMessageBox({
                title: "<i class='fa fa-sign-out txt-color-orangeDark'></i> ERROR: Failure while communicating to server... <span class='txt-color-orangeDark'></span>",
                content: "Please close this browser tab and try again.<br /> Contact support if this error persists.",
                buttons: "[Close]"
            });
        }
    });

    self.all_count = ko.observable(0);
    self.register_set_len = ko.observable(0);
    self.poller_names = ko.observableArray([]);
    self.poll_list_len = ko.observable(0);
    self.pollers = ko.observableArray([]);
    self.user_gid = ko.observable("");

    self.asUser = function () {
        self.api.serviceAsUser({id: self.user_gid()}, function () {
            window.location = '/i.html#!/dashboard.html';
        });
    };

    self.refresh = function () {
        self.api.serviceGet(function (data) {
            self.all_count(data.all_count);
            self.register_set_len(data.register_set_len);
            self.poller_names(data.poller_names);
            self.poll_list_len(data.poll_list_len);
            var mappedPollers = $.map(data.pollers, function (item) { return new PollerStats(item); });
            self.pollers(mappedPollers);
        });
    }
}