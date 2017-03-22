import Collection from 'girder/collections/Collection';
import TransferModel from '../models/TransferModel';

var TransferCollection = Collection.extend({
    resourceName: 'dm/transfer',
    model: TransferModel
});

export default TransferCollection;
