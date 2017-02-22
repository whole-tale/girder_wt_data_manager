import Collection from 'girder/collections/Collection';
import ContainerModel from '../models/ContainerModel';

var ContainerCollection = Collection.extend({
    resourceName: 'dm/testing/container',
    model: ContainerModel
});

export default ContainerCollection;
