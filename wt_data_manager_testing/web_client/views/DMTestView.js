import _ from 'underscore';

import View from 'girder/views/View';
import ContainerCollection from '../collections/ContainerCollection.js'

import DMTestViewTemplate from '../templates/dmTestViewTemplate.pug';
import '../stylesheets/dmTestView.styl';

var DMTestView = View.extend({
    initialize: function () {
        console.log("Initialize");
        this.containers = new ContainerCollection();
        this.containers.on('g:changed', function () {
            this.render();
        }, this);
        this.containers.fetch();
        this.render();
    },

    render: function () {
        console.log("Render");
        console.log("Containers: ", this.containers);
        this.$el.html(DMTestViewTemplate({
            containers: this.containers.toArray()
        }));
        return this;
    }
});

export default DMTestView;
