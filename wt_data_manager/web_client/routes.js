import router from 'girder/router';
import events from 'girder/events';
import { restRequest } from 'girder/rest';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('wt_data_manager', 'plugins/wt_data_manager/config');

import ConfigView from './views/ConfigView';
router.route('plugins/wt_data_manager/config', 'DMConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});


