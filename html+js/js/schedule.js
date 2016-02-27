function Schedule(data) {
    var self = this;
    self.ignore = ['tz_picker', 'tz_offset', 'dayMockArrayBase', 'dayMockArray', 'dayTitleArray', 'enabled'];
    // on - true if schedule is enabled, s - array of "on" hours of week, 0 is mon : 00:00 -- mon : 00:59
    self.data = data ? data : { on: false, s: [] };

    self.tz_picker = null;
    self.tz_offset = 0;

    // schedule model, each hour is represented by a button
    // internal representation is always in UTC
    self.dayMockArrayBase = [];
    self.dayMockArray = ko.observableArray([]);
    self.dayTitleArray = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

    self.parseOffset = function (offset_str) {
        var s = offset_str.split(':');
        var h = parseInt(s[0]);
        var m = parseInt(s[1]);
        return h;
    }

    self.offsetHour = function (hour, offset) {
        var h = hour + offset;
        if (h < 0 /*24 * 7*/) {
            h = h + 168;
        } else if (h >= 168) {
            h = h - 168;
        }
        return h;
    }

    self.enabled = ko.observable(self.data.on);

    self.enabled.subscribe(function (value) {
        self.data.on = value ? true : false;
        self.dayMockArray(self.dayMockArrayBase);
    });


    self.getClass = function (hour) {
        // adjust hour to local TZ      
        if (self.data.s.indexOf(self.offsetHour(hour, self.tz_offset)) >= 0) {
            return 'btn-success';
        }
        else {
            return 'btn-danger';
        }
    }

    self.toggle = function (link, node) {
        var idl = node.target.id.split('-');
        // adjust to local TZ
        var hour = self.offsetHour(parseInt(idl[1]), self.tz_offset);

        var idx = self.data.s.indexOf(hour);
        if (idx >= 0) {
            self.data.s.splice(idx, 1);
        }
        else {
            self.data.s.push(hour);
        }

        if (self.data.s.length > 1) {
            $(node.target).removeClass("btn-success btn-danger").addClass(idx >= 0 ? "btn-danger" : "btn-success");
        }
        else {

            self.dayMockArray([]);
            self.dayMockArray(self.dayMockArrayBase);
        }
    }

    self.create = function () {
        // local TZ
        var d = new Date();
        self.tz_offset = d.getTimezoneOffset() / 60;
        // init mock array
        for (var i = 0; i < 7; ++i) {
            self.dayMockArrayBase.push({
                dayTitle: self.dayTitleArray[i],
                dayIndex: i,
                getId: function (hour) {
                    return 's-' + (this.dayIndex * 24 + hour);
                },
                toggle: self.toggle,
                getClass: function (hour) {
                    return self.getClass(this.dayIndex * 24 + hour);
                }
            });
        }

        self.dayMockArray(self.dayMockArrayBase);
    };

    self.create();

    // init timezone picker
    self.init = function (uid) {
        self.tz_picker = $('#tz-' + uid).timezones();
        $(self.tz_picker).change(function () {
            var offset_str = $(this).find('option[value="' + this.value + '"]').data().offset;
            var offset = self.parseOffset(offset_str);
            self.data.s = $.map(self.data.s, function (item) {
                return self.offsetHour(item, (self.tz_offset + offset));
            });

            self.dayMockArray([]);
            self.dayMockArray(self.dayMockArrayBase);
        });
        // check if "paste" button to be enabled
        if (localStorage.getItem('MRSCHEDULE') != null) {
            $('.btn-schedule-paste').removeAttr('disabled');
        }
    };

    // button events
    self.copy = function () {
        localStorage.setItem('MRSCHEDULE', JSON.stringify(self.data));
        // using jquery to enable all disabled paste buttons
        $('.btn-schedule-paste').removeAttr('disabled');
    }

    self.paste = function () {
        var sch_str = localStorage.getItem('MRSCHEDULE');
        if (sch_str) {
            self.data = JSON.parse(sch_str);
            self.dayMockArray([]);
            self.dayMockArray(self.dayMockArrayBase);
        }
    }

    self.invert = function () {
        var inverted = [];
        for (var i = 0; i < 168; ++i) {
            if (self.data.s.indexOf(i) < 0) {
                inverted.push(i);
            }
        }
        self.data.s = inverted;
        self.dayMockArray([]);
        self.dayMockArray(self.dayMockArrayBase);
    }

    self.clear = function () {
        self.data.s = [];
        self.dayMockArray([]);
        self.dayMockArray(self.dayMockArrayBase);
    }
}