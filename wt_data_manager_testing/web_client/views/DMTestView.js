import _ from 'underscore';

import View from 'girder/views/View';
import ContainerCollection from '../collections/ContainerCollection.js'
import TransferCollection from '../collections/TransferCollection.js'

import DMTestViewTemplate from '../templates/dmTestViewTemplate.pug';
import '../stylesheets/dmTestView.styl';
import TransferStatus from '../constants.js'

function addBitsToTransfer(transfer) {
    transfer.set('stringStatus', TransferStatus.toString(transfer.get('status')));
    var crt = transfer.get('transferred');
    var total = transfer.get('size');
    if (crt && total) {
        transfer.set('progress', Math.round(crt * 100 / total));
    }
    else {
        transfer.set('progress', 0);
    }
}

function addBits(transfers) {
    console.log("TransferStatus: ", TransferStatus);
    var addFake = false;
    if (transfers != null) {
        if (transfers.length == 0) {
            addFake = true;
        }
        else if (transfers.at(0).get('_id') != 1) {
            addFake = true;
        }
    }
    if (addFake) {
        transfers.push({'_id': 1, 'ownerId': 0, 'sessionId': 0,
            'itemId': 0, 'status': TransferStatus.TRANSFERRING, 'error': null, 'size': 100,
            'transferred': 50, 'path': '/fake/path'});
    }
    for (var i = 0; i < transfers.length; i++) {
        console.log("Transfers[" + i + "]:", transfers.at(i));
        addBitsToTransfer(transfers.at(i));
    }
    return transfers;
}

var DMTestView = View.extend({
    initialize: function () {
        console.log("Initialize");
        this.containers = new ContainerCollection();
        this.transfers = new TransferCollection();
        this.containers.on('g:changed', function() {
            this.render();
        }, this);
        this.transfers.on('g:changed', function() {
            this.render();
        }, this);
        this.update(this);
    },

    update: function(obj) {
        obj.containers.fetch();
        obj.transfers.fetch();
        obj.render();
        setTimeout(function() {obj.update(obj);}, 5000);
    },

    render: function () {
        console.log("Render");
        console.log("Containers: ", this.containers);
        var transfers = addBits(this.transfers);
        console.log("Transfers: ", transfers);
        this.$el.html(DMTestViewTemplate({
            containers: this.containers.toArray(),
            transfers: transfers.toArray(),
        }));
        return this;
    }
});

export default DMTestView;
