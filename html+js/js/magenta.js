function MagentaApi(onError) {
    var self = this;
    self.onError = onError;
    self.handlersWorking = [];
    self.handlersIdle = [];

    self.addWorkingHandler = function (handler) {
        self.handlersWorking.push(handler);
    }

    self.addIdleHandler = function (handler) {
        self.handlersIdle.push(handler);
    }

    self.beforeSend = function () {
        $.each(self.handlersWorking, function (idx, handler) {
            handler();
        });
    }
    self.complete = function () {
        $.each(self.handlersIdle, function (idx, handler) {
            handler();
        });
    }

    self.userGet = function (node, onComplete) {
        $.ajax({
            url: '/a/api/v1/user/' + node,
            dataType: 'json',
            cache: false,
            type: 'GET',
            data: '',
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            },
            beforeSend: self.beforeSend,
            complete: self.complete
        });
    }
    self.viewGet = function (node, onComplete) {
        $.ajax({
            url: '/a/api/v1/view/' + node,
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
    self.accountAdd = function (data, onComplete) {
        $.ajax("/a/api/v1/account/add", {
            data: ko.toJSON(data),
            type: "post",
            dataType: "json",
            contentType: "application/json",
            success: function (result) {
                onComplete(result);
            },
            error: function (response) {
                self.onError(response.status);
            },
            beforeSend: self.beforeSend,
            complete: self.complete
        });
    }
    self.accountRemove = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/account/remove',
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
    self.viewSelector = function (onComplete, params) {
        $.ajax({
            url: '/a/api/v1/view/selector',
            dataType: 'json',
            cache: false,
            type: 'GET',
            data: params,
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }
    self.accountLink = function (links, onComplete) {
        $.ajax({
            url: '/a/api/v1/account/link',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(links),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }
    self.accountUnlink = function (links, onComplete) {
        $.ajax({
            url: '/a/api/v1/account/unlink',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(links),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }
    self.accountSave = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/account/save',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }
    self.accountSync = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/account/sync',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }

    self.sourceForget = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/source/forget',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }

    self.sourceClone = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/source/clone',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }

    self.sourcePoke = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/source/poke',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            }
        });
    }
    self.agreeTerms = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/user/agree',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            },
            beforeSend: self.beforeSend,
            complete: self.complete
        });
    }
    self.updateInfo = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/user/info',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            },
            beforeSend: self.beforeSend,
            complete: self.complete
        });
    }
    self.deleteAccount = function (data, onComplete) {
        $.ajax({
            url: '/a/api/v1/user/remove',
            dataType: 'json',
            cache: false,
            type: 'POST',
            data: ko.toJSON(data),
            success: function (data) {
                onComplete(data);
            },
            error: function (response) {
                self.onError(response.status);
            },
            beforeSend: self.beforeSend,
            complete: self.complete
        });
    }
}