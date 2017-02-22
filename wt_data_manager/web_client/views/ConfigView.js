import _ from 'underscore';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import { apiRoot, restRequest } from 'girder/rest';
import events from 'girder/events';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit .g-oauth-provider-form': function (event) {
            event.preventDefault();
            var providerId = $(event.target).attr('provider-id');
            this.$('#g-oauth-provider-' + providerId + '-error-message').empty();

            this._saveSettings([{
                key: 'dm.private_storage_path',
                value: this.$('#g-wt-dm-private-storage-path').val().trim()
            }]);
        }
    },

    initialize: function () {
        var settingKeys = [];
        settingKeys.push('dm.private_storage_path');

        restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settingKeys)
            }
        }).done(_.bind(function (resp) {
            console.log("Settings: ", resp);
            this.settingVals = resp;
            this.render();
        }, this));
    },

    render: function () {
        var origin = window.location.protocol + '//' + window.location.host;
        var _apiRoot = apiRoot;

        if (apiRoot.substring(0, 1) !== '/') {
            _apiRoot = '/' + apiRoot;
        }

        this.$el.html(ConfigViewTemplate({
            origin: origin,
            apiRoot: _apiRoot,
        }));

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'WholeTale Data Manager',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        if (this.settingVals) {
            this.$('#g-wt-dm-private-storage-path').val(
                this.settingVals['dm.private_storage_path']);
        }

        return this;
    },

    _saveSettings: function (providerId, settings) {
        restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 3000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-wt-dm-config-error-message').text(resp.responseJSON.message);
        }, this));
    }
});

export default ConfigView;

