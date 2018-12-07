import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

import ConfigView from './views/ConfigView';

exposePluginConfig('wt_data_manager', 'plugins/wt_data_manager/config');

router.route('plugins/wt_data_manager/config', 'DMConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
