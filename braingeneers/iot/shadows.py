import requests

class DatabaseInteractor:
    """
    This class provides methods for interacting with the Strapi Shadows database.

    See documentation at: ...

    Assumes the following:
        - The Strapi database is running at the endpoint specified in the constructor
        - User has an API key for the Strapi database

    Public functions:

        #
        # List and register IoT devices
        #
        list_devices(**filters)  # list connected devices, filter by one or more state variables.
        create_device(device_name: str, device_type: str)  # create a new device if it doesn't already exist

        #
        # Get/set/update/subscribe to device state variables
        #
        # todo:
            get_device_state(device_name: str)  # returns the device shadow file as a dictionary.
            update_device_state(device: str, device_state: dict)  # updates one or more state variables for a registered device.
            set_device_state(device_name: str, state: dict)  # saves the shadow file, a dict that is JSON serializable.
            subscribe_device_state_change(device: str, device_state_keys: List[str], callback: Callable)  # subscribe to notifications when a device state changes.

    """
    def __init__(self, endpoint, api_token) -> None:
        self.endpoint = endpoint
        self.token = api_token
    
    class __API_object:
        """
        This class is used to represent objects in the database as python objects
        """
        def __init__(self, endpoint, api_token):
                self.endpoint = endpoint
                self.token = api_token
                self.id = None
                self.attributes = {}

        def __str__(self):
            var_list = filter(lambda x: x not in ["endpoint", "token"], vars(self))
            return str({var: getattr(self, var) for var in var_list})
            # return str(vars(self))
        #json representation of the thing
        def to_json(self):
            return vars(self)

        def parse_API_response(self, response_data):
            self.id = response_data['id']
            self.attributes = response_data['attributes']
            for key in self.attributes:
                # print(key, self.attributes[key])
                if type(self.attributes[key]) is dict and "data" in self.attributes[key]:
                    if self.attributes[key]["data"] is not None and len(self.attributes[key]["data"]) != 0:
                        # print("found data", self.attributes[key]["data"])
                        item_list = []
                        if type(self.attributes[key]["data"]) is list:
                            for item in self.attributes[key]["data"]:
                                # print("item", item)
                                if "id" in item:
                                    item_list.append(item["id"])
                        else:
                            item_list.append(self.attributes[key]["data"]["id"])

                        self.attributes[key] = item_list
                    else:
                        self.attributes[key] = []

    class Thing(__API_object):
        def update_thing_on_database(self):
            url = self.endpoint + "/interaction-things/" + str(self.id) + "?populate=%2A"
            headers = {"Authorization": "Bearer " + self.token}
            data = {"data": self.attributes}
            response = requests.put(url, headers=headers, json=data)
            print(response.json())
            print(response.status_code)
            self.parse_API_response(response.json()['data'])

        def create(self):
            url = self.endpoint + "/interaction-things?filters[name][$eq]=" + self.attributes["name"]
            headers = {"Authorization": "Bearer " + self.token}
            response = requests.get(url, headers=headers)
            if len(response.json()['data']) == 0:
                # thing = self.Thing(type, name)
                api_url = self.endpoint+"/interaction-things/"
                data = {"data": self.attributes}
                response = requests.post(api_url, json=data, headers={
                                        'Authorization': 'bearer ' + self.token})
                # print(response.status_code)
                # print(response.json())
                if response.status_code == 200:
                    self.id = response.json()['data']['id']
            else:
                print("thing already exists")
                print(response.json())
                try:
                    self.parse_API_response(response.json()['data'][0])
                except KeyError:
                    print("some values are missing")


    class Experiment(__API_object):
        pass
    class Plate(__API_object):
        pass
    class Well(__API_object):
        pass

    def create_interaction_thing(self, type, name):
        thing = self.Thing(self.endpoint, self.token)
        thing.attributes["name"] = name
        thing.attributes["type"] = type
        thing.create()
        return thing
    
    def upload_interaction_thing(self, type, name):
        url = self.endpoint + "/interaction-things?filters[name][$eq]=" + name
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        if len(response.json()['data']) == 0:
            thing = self.Thing(type, name)
            api_url = self.endpoint+"/interaction-things/"
            info = {
                "data": {
                    "name": name,
                    "type": type
                }
            }
            response = requests.post(api_url, json=info, headers={
                                    'Authorization': 'bearer ' + self.token})
            # print(response.status_code)
            # print(response.json())
            if response.status_code == 200:
                thing.id = response.json()['data']['id']
            return thing
        else:
            print("thing already exists")
            print(response.json())
            try:
                thing = self.Thing()
                thing.parse_API_response(response.json()['data'][0])
            except KeyError:
                print("some values are missing")
            return thing

    def add_to_shadow(self, thing, json):
        if thing.attributes["shadow"] is None:
            thing.attributes["shadow"] = json
        else:
            for key, value in json.items():
                thing.attributes["shadow"][key] = value

        return self.update_thing_on_database(thing)


    def __get_id_from_name(self, object_type, name):
        url = self.endpoint + "/" + object_type + "?filters[name][$eq]=" + name
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        if len(response.json()['data']) == 0:
            return None
        else:
            return response.json()['data'][0]['id']

    """
    add_plate_to_thing

    updates the current plate of the thing and adds the plate to the list of all plates historically associated with the thing.
    The plates list relation also updates the thing relation on the plate object itself. 
    """
    def add_plate_to_thing(self, thing, plate):
        api_url = self.endpoint + "/interaction-things/" + str(thing.id) + "?populate=%2A"
        headers = {"Authorization": "Bearer " + self.token}
        if thing.attributes["plates"] is None:
            thing.attributes["plates"] = []
        thing.attributes["plates"].append(plate.id)
        info = {
            "data": {
                "current_plate": plate.id,
                "plates": thing.attributes["plates"]

            }
        }
        response = requests.put(api_url, headers=headers, json=info)
        thing.parse_API_response(response.json()["data"])
        return thing

    """
    add_thing_to_plate

    adds the thing to the list of things associated with the plate. also updates the plate relation on the thing object itself.
    does not effect current_plate value
    """
    def add_thing_to_plate(self, thing, plate):
        api_url = self.endpoint + "/plates/" + str(plate.id) + "?populate=%2A"
        headers = {"Authorization": "Bearer " + self.token}
        if plate.attributes["interaction_things"] is None:
            plate.attributes["interaction_things"] = []

        plate.attributes["interaction_things"].append(thing.id)
        info = {
            "data": {
                "interaction_things": plate.attributes["interaction_things"]
            }
        }
        response = requests.put(api_url, headers=headers, json=info)
        if response.status_code == 200:
            plate.parse_API_response(response.json()["data"])
            return plate
        else:
            print("error adding thing to plate")
            return None

    def add_experiment_to_thing(self, thing, experiment):
        api_url = self.endpoint + "/interaction-things/" + str(thing.id) + "?populate=%2A"
        headers = {"Authorization": "Bearer " + self.token}
        info = {
            "data": {
                "current_experiment": experiment.id
            }
        }
        response = requests.put(api_url, headers=headers, json=info)
        print(response.status_code)
        print(response.json())
        thing.parse_API_response(response.json()["data"])
        return thing




    def get_thing(self, name):
        url = self.endpoint + "/interaction-things?filters[name][$eq]=" + name
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        if len(response.json()['data']) == 0:
            print("Interaction thing not found")
            return None
        try:
            thing = self.Thing()
            thing.id = response.json()['data'][0]['id']
            thing.name = response.json()['data'][0]['attributes']["name"]
            thing.type = response.json()['data'][0]['attributes']["type"]
            thing.shadow = response.json()['data'][0]['attributes']["shadow"]
            thing.current_experiment = response.json()['data'][0]["current_experiment"]
            thing.current_plate = response.json()['data'][0]["current_plate"]
        except KeyError:
                print("some values are missing")
        print(response.json())
        return thing

    def add_thing_to_database(self, thing): 
        ##very limited usefullness, doesn't update existing things, only adds if they don't exist
        url = self.endpoint + "/interaction-things?filters[name][$eq]=" + thing.name
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        if len(response.json()['data']) == 0:
            api_url = self.endpoint + "/interaction-things/"
            # print(api_url)
            headers = {"Authorization": "Bearer " + self.token}
            info = {
                "data": {
                    "name": thing.name,
                    "description": "",
                    "type": thing.type,
                    "shadow": thing.shadow
                }
            }

            response = requests.post(api_url, headers=headers, json=info)
            # response = requests.post(api_url, json=info, headers={
            #                         'Authorization': 'bearer ' + self.token})
            return response.json()
        else:
            print("Interaction thing already exists")
            return response.json()

    def update_thing_on_database(self, thing):
        url = self.endpoint + "/interaction-things/" + str(thing.id) + "?populate=%2A"
        headers = {"Authorization": "Bearer " + self.token}
        # filtered = thing.attributes
        # filtered = dict(filter(lambda key: key[0] not in ["createdAt", "updatedAt", "publishedAt"], thing.attributes.items()))
        # print("filtered", filtered)
        data = {"data": thing.attributes}
        # data = {
        #     "data": {
        #         "name": thing.attributes["name"],
        #         "type": thing.attributes["type"],
        #         "shadow": thing.attributes["shadow"],
        #         "current_experiment": 10
        #     }
        # }
        response = requests.put(url, headers=headers, json=data)
        print(response.json())
        print(response.status_code)
        thing.parse_API_response(response.json()['data'])
        return thing

 

    def create_plate(self, name, rows, columns):
        url = self.endpoint + "/plates?filters[name][$eq]=" + name + "&populate=%2A"
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        if len(response.json()['data']) == 0:
            plate = self.Plate(name, rows, columns)
            api_url = self.endpoint+"/plates/"
            image_params = {
                "images": True,
                "uuids": [
                    "2022-07-11-i-connectoid-3",
                    "2020-02-07-fluidics-imaging-2"
                ],
                "group_id": "C"
            }
            info = {
                "data": {
                    "name": name,
                    "rows": rows,
                    "columns": columns,
                    "image_parameters": image_params
                }
            }
            response = requests.post(api_url, json=info, headers={
                                    'Authorization': 'bearer ' + self.token})
            print(response.status_code)
            print(response.json())
            if response.status_code == 200:
                wells = self.__generate_wells_for_plate(response.json()['data']['id'], rows, columns)
                plate.wells = wells
                plate.id = response.json()['data']['id']

            return plate
        else:
            print("Plate already exists")
            # print(response.json())
            plate = self.Plate()
            plate.parse_API_response(response.json()['data'][0])
            return  plate

    def sync_plate(self, plate):
        if plate.id:
            api_url = self.endpoint+"/plates/" + str(plate.id)
            image_params = {
                "images": True,
                "uuids": [
                    "2022-07-11-i-connectoid-3",
                    "2020-02-07-fluidics-imaging-2"
                ],
                "group_id": "C"
            }
            info = {
                "data": {
                    "name": plate.name,
                    "rows": plate.rows,
                    "columns": plate.columns,
                    "image_parameters": image_params,
                    "wells": plate.wells
                }
            }
            response = requests.put(api_url, json=info, headers={
                                    'Authorization': 'bearer ' + self.token})
            print(response.status_code)
            print(response.json())
            return plate


    def __generate_wells_for_plate(self, plate_id, rows, columns):
        api_url = self.endpoint+"/wells/"
        wells_list = []
        for i in range(1, rows+1):
            for j in range(1, columns+1):
                info = {
                    "data": {
                        "name": str(i) + str(j),
                        "position_index": str(i) + str(j),
                        "plate": plate_id
                    }
                }
                response = requests.post(api_url, json=info, headers={
                                        'Authorization': 'bearer ' + self.token})
                # print(response.status_code)
                if( response.status_code == 200):
                    wells_list.append(response.json()['data']['id'])
                else:
                    print("Failed to create well")
                # print(response.json())
        return wells_list

    def pull_plate(self, plate):
        plate = self.get_plate(plate.id)
        return plate

    def get_plate(self, plate_id):
        url = self.endpoint + "/plates/" + str(plate_id) + "?populate=%2A"
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        if len(response.json()['data']) == 0:
            print("Plate doesn't exist")
            return None
        else:
            print("Plate exists")
            plate = self.Plate()
            plate.parse_API_response(response.json()['data'])
            return plate



    def create_experiment(self, name, description):
        url = self.endpoint + "/experiments?filters[name][$eq]=" + name
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        
        if len(response.json()['data']) == 0:
            experiment = self.Experiment(name, description)
            api_url = self.endpoint+"/experiments/"
            info = {
                "data": {
                    "name": name,
                    "description": description,
                }
            }
            response = requests.post(api_url, json=info, headers={
                                    'Authorization': 'bearer ' + self.token})
            # print(response.status_code)
            # print(response.json())
            if response.status_code == 200:
                experiment.id = response.json()['data']['id']

            return experiment
        else:
            print("Experiment already exists")
            experiment = self.Experiment()
            experiment.parse_API_response(response.json()['data'][0])
            return experiment
        
    def sync_experiment(self, experiment):
        if experiment.id:
            api_url = self.endpoint+"/experiments/" + str(experiment.id)
            info = {
                "data": {
                    "name": experiment.name,
                    "description": experiment.description,
                    "plates": experiment.plates
                }
            }
            response = requests.put(api_url, json=info, headers={
                                    'Authorization': 'bearer ' + self.token})
            print(response.status_code)
            print(response.json())
            return experiment

    def get_experiment(self, experiment_id):
        url = self.endpoint + "/experiments/" + str(experiment_id) + "?populate=%2A"
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        if len(response.json()['data']) == 0:
            print("Experiment doesn't exist")
            return None
        else:
            print("Experiment exists")
            experiment = self.Experiment()
            attributes = response.json()['data']['attributes']
            for key in attributes:
                # print(key, attributes[key])
                # if attributes[key] is type dict:
                if type(attributes[key]) is dict and "data" in attributes[key]:
                    if len(attributes[key]["data"]) != 0:
                        list = []
                        for item in attributes[key]["data"]:
                            if "id" in item:
                                list.append(item["id"])

                        # print(list)
                        # print(attributes[key]["data"])
                        setattr(experiment, key, list)
                else:
                    setattr(experiment, key, attributes[key])
                    # print(attributes[key])
                    # print("is dict")
                    # plate[key] = attributes[key]
                # plate[key] = response.json()['data'][key]
            experiment.id = response.json()['data']['id']
            return experiment



## here begins the old ones
#     def create_interaction_thing(self, name, interaction_type, description="", shadow={}):
#         url = self.endpoint + "/interaction-things?filters[name][$eq]=" + name
#         headers = {"Authorization": "Bearer " + self.token}
#         response = requests.get(url, headers=headers)
#         if len(response.json()['data']) == 0:
#             api_url = self.endpoint + "/interaction-things/"
#             # print(api_url)
#             headers = {"Authorization": "Bearer " + self.token}
#             info = {
#                 "data": {
#                     "name": name,
#                     "description": description,
#                     "type": interaction_type,
#                     "shadow": shadow
#                 }
#             }

#             response = requests.post(api_url, headers=headers, json=info)
#             # response = requests.post(api_url, json=info, headers={
#             #                         'Authorization': 'bearer ' + self.token})
#             return response.json()
#         else:
#             print("Interaction thing already exists")
#             return response.json()

#     # def update_values_on_interaction_thing(self, name, values={}):
#     #     interaction_thing_id = self.get_interaction_thing_id_from_name(name)
#     #     data =
#     #     self.update_shadow_without_overwrite(interaction_thing_id, values)


#     def update_experiment_on_interaction_thing(self, interaction_thing_id, experiment_id):
#         url = self.endpoint + "/interaction-things/" + str(interaction_thing_id)
#         headers = {"Authorization": "Bearer " + self.token}
#         data = {
#             "experiment_id": experiment_id
#         }
#         response = requests.put(url, headers=headers, json=data)
#         return response


#     def update_plate_on_interaction_thing(self, interaction_thing_id, plate_id):
#         url = self.endpoint + "/interaction-things/" + str(interaction_thing_id)
#         headers = {"Authorization": "Bearer " + self.token}
#         data = {
#             "plate_id": plate_id
#         }
#         response = requests.put(url, headers=headers, json=data)
#         return response

#     def get_interaction_thing_id_from_name(self, name):
#         url = self.endpoint + "/interaction-things?filters[name][$eq]=" + name
#         headers = {"Authorization": "Bearer " + self.token}
#         response = requests.get(url, headers=headers)
#         print(response.json())
#         return response.json()['data'][0]['id']

#     def update_shadow_without_overwrite(self, interaction_thing_id, shadow):
#         url = self.endpoint + "/interaction-things/" + str(interaction_thing_id)
#         headers = {"Authorization": "Bearer " + self.token}
#         data = {
#             "shadow": shadow
#         }
#         response = requests.put(url, headers=headers, json=data)
#         return response

#     def list_all_interaction_things(self):
#         url = self.endpoint + "/interaction-things"
#         headers = {"Authorization": "Bearer " + self.token}
#         response = requests.get(url, headers=headers)
#         return response.json()

# ## Experiments

# ## Experiments
# #     Create, delete, update, get, list

#     ##create methods:
#     # def create_experiment(self, name, description):
#     #     api_url = self.endpoint+"/experiments/"
#     #     info = {
#     #         "data": {
#     #             "name": name,
#     #             "description": description
#     #         }
#     #     }
#     #     response = requests.post(api_url, json=info, headers={
#     #                             'Authorization': 'bearer ' + self.token})
#     #     print(response.status_code)
#     #     print(response.json())
#     #     return response.json()['data']['id']

#     # def generate_plate_for_experiment(self, experiment_id, plate_name):
#     #     plate_id = self.create_plate(plate_name, 2, 3)
#     #     self.add_plate_to_experiment_without_overwriting(experiment_id, plate_id)
#     #     return plate_id

#     ## update methods:
#     def add_plate_to_experiment(self, experiment_id, plate_id):
#         api_url = self.endpoint+"/experiments/"+str(experiment_id)
#         info = {
#             "data": {
#                 "plates": [plate_id]
#             }
#         }
#         response = requests.put(api_url, json=info, headers={
#             'Authorization': 'bearer ' + self.token})
#         print(response.status_code)
#         print(response.json())

#     def add_plate_to_experiment_without_overwriting(self, experiment_id, plate_id):
#         experiment = self.get_experiment(experiment_id) 
#         # experiment['data']['attributes']['plates']['data']['id'].append(plate_id) 
#         plates = [] 
#         for i in experiment['data']['attributes']['plates']['data']:
#             print(i['id'])
#             plates.append(str(i['id']))
#         # print(experiment['data']['attributes']['plates']['data'][0]['id'])  
#         plates.append(str(plate_id)) 
#         api_url = self.endpoint+"/experiments/"+str(experiment_id)
#         info = {
#             "data": {
#                 "plates": plates
#             }
#         }
#         response = requests.put(api_url, json=info, headers={
#             'Authorization': 'bearer ' + self.token})
            
#         print(response.status_code)
#         print(response.json())

#     ## get methods:
#     def get_experiment(self, experiment_id):
#         api_url = self.endpoint+"/experiments/"+str(experiment_id)+"?populate=%2A"
#         response = requests.get(api_url, headers={
#             'Authorization': 'bearer ' + self.token})
#         # print(response.status_code)
#         # print(response.json())
#         return response.json()

#     def list_experiments(self):
#         api_url = self.endpoint+"/experiments/"
#         response = requests.get(api_url, headers={
#             'Authorization': 'bearer ' + self.token})
#         # print(response.status_code)
#         # print(response.json())
#         return response.json()

#     ## Plates
#     # def create_plate(self, name, rows, columns):
#     #     api_url = self.endpoint+"/plates/"
#     #     image_params = {
#     #         "images": True,
#     #         "uuids": [
#     #             "2022-07-11-i-connectoid-3",
#     #             "2020-02-07-fluidics-imaging-2"
#     #         ],
#     #         "group_id": "C"
#     #     }
#     #     info = {
#     #         "data": {
#     #             "name": name,
#     #             "rows": rows,
#     #             "columns": columns,
#     #             "image_parameters": image_params
#     #         }
#     #     }
#     #     response = requests.post(api_url, json=info, headers={
#     #                             'Authorization': 'bearer ' + self.token})
#     #     print(response.status_code)
#     #     print(response.json())
#     #     if response.status_code == 200:
#     #         self.generate_wells_for_plate(
#     #             response.json()['data']['id'], rows, columns)

#     #     return response.json()['data']['id']


#     # def generate_wells_for_plate(self, plate_id, rows, columns):
#     #     api_url = self.endpoint+"/wells/"
#     #     for i in range(1, rows+1):
#     #         for j in range(1, columns+1):
#     #             info = {
#     #                 "data": {
#     #                     "name": str(i) + str(j),
#     #                     "position_index": str(i) + str(j),
#     #                     "plate": plate_id
#     #                 }
#     #             }
#     #             response = requests.post(api_url, json=info, headers={
#     #                                     'Authorization': 'bearer ' + self.token})
#     #             print(response.status_code)
#     #             # print(response.json())


#     ## update methods:




#     ## get methods:
#     def get_plate_by_name(self, name):
#         api_url = self.endpoint+"/plates/?filters[name][$eq]="+name
#         response = requests.get(api_url, headers={
#             'Authorization': 'bearer ' + self.token})

#         return response.json()

#     def get_plate(self, plate_id):
#         api_url = self.endpoint+"/plates/"+str(plate_id)+"?populate=%2A"
#         response = requests.get(api_url, headers={
#             'Authorization': 'bearer ' + self.token})

#         return response.json()

#     def list_all_plates(self):
#         api_url = self.endpoint+"/plates/"
#         response = requests.get(api_url, headers={
#             'Authorization': 'bearer ' + self.token})

#         return response.json()

# ## Wells

#     def create_well(self, name, position_index, plate_id):
#         api_url = self.endpoint+"/wells/"
#         info = {
#             "data": {
#                 "name": name,
#                 "position_index": position_index,
#                 "plate": plate_id
#             }
#         }
#         response = requests.post(api_url, json=info, headers={
#                                 'Authorization': 'bearer ' + self.token})
#         print(response.status_code)
#         print(response.json())
#         return response.json()['data']['id']

#     def delete_well(self, well_id):
#         api_url = self.endpoint+"/wells/"+str(well_id)
#         response = requests.delete(api_url, headers={
#             'Authorization': 'bearer ' + self.token})
#         print(response.status_code)
#         print(response.json())

#     def delete_all_wells(self):
#         # this is a mess forget about it for now
#         api_url = self.endpoint+"/wells?pagination[pageSize]=100"
#         response = requests.get(
#             api_url, headers={'Authorization': 'bearer ' + self.token})
#         wells = response.json()
#         num_pages = wells['meta']['pagination']['pageCount']
#         for well in wells['data']:
#             # print(well['id'])
#             api_url = "http://localhost:1337/api/wells/" + str(well['id'])
#             response = requests.delete(
#                 api_url, headers={'Authorization': 'bearer ' + self.token})
#             print(response.status_code)
#             # if response.status_code != 200:
#             #     return
#             # get next page of wells
#             # time.sleep(1)
# ## generalize?

# # Objects


