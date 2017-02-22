import router from 'girder/router';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

import DMTestView from './views/DMTestView';

router.route('dm/testing', 'dmTesting', function() {
    console.log("Test");
    events.trigger('g:navigateTo', DMTestView);
})

function addRestRoute(localPath, name, httpMethod, eventName, pathFunction) {
    router.route(localPath, name, function(params) {
        restRequest({
            path: pathFunction(params),
            type: httpMethod,
            data: {},
            error: null
        }).done(_.bind(function (event) {
            console.log(name + " request done");
            this.trigger(eventName, event);
        }, this)).error(_.bind(function (err) {
            console.log(name + " request error", err);
            this.trigger('g:error', err);
        }, this));
        console.log(name + " request sent");
        events.trigger('g:navigateTo', DMTestView);;
    });
}

addRestRoute('dm/testing/createContainer', 'dmTestingCreateContainer', 'POST', 'g:dm-test-container-created',
    function(params) {
        return 'dm/testing/container'
    }
);

addRestRoute('dm/testing/container/:id/start', 'dmTestingStartContainer', 'GET', 'g:dm-test-container-started',
    function(id) {
        return 'dm/testing/container/' + id + '/start';
    }
);

addRestRoute('dm/testing/container/:id/stop', 'dmTestingStopContainer', 'GET', 'g:dm-test-container-stopped',
    function(id) {
        return 'dm/testing/container/' + id + '/stop';
    }
);

addRestRoute('dm/testing/container/:id/remove', 'dmTestingRemoveContainer', 'DELETE', 'g:dm-test-container-removed',
    function(id) {
        return 'dm/testing/container/' + id;
    }
);
