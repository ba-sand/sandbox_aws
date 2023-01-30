import subprocess
import os
import glob
import yaml

def run_bash(command:str):
   process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
   output, error = process.communicate()
   return output.decode("utf-8")

if __name__ == "__main__":
   path = 'lambda_routes/'
   lambdas_to_deploy = []

   # read in lambdas and determine which should be deployed
   for filename in glob.glob(os.path.join(path, '*.yaml')):
      with open(os.path.join(os.getcwd(), filename), 'r') as f: # open in readonly mode
         output = yaml.safe_load(f)
         if output['deploy'] is True:
            lambdas_to_deploy.append(output)

   policy = '"{\"Version\": \"2012-10-17\",\"Statement\": [{\"Effect\": \"Allow\", \"Principal\": \"*\",\"Action\": \"execute-api:Invoke\",\"Resource\": \"arn:aws:execute-api:us-east-1:482102633168:iljanrzfyi\/*\" },{\"Effect\": \"Deny\", \"Principal\": \"*\",\"Action\": \"execute-api:Invoke\", \"Resource\": \"arn:aws:execute-api:us-east-1:482102633168:iljanrzfyi\/*\", \"Condition\": { \"NotIpAddress\": { \"aws:SourceIp\": \"104.12.69.239\/32\"}}}]}"'

   # deploy the lambdas that are indicated as such
   for cur_lambda in lambdas_to_deploy:
      # extract data from yamls
      api_name = cur_lambda['name']
      api_desc = cur_lambda['description']
      lambda_url = cur_lambda['url']
      function_aws = cur_lambda['function_aws']

      # get list of existing APIs
      cmd_1 = 'aws apigateway get-rest-apis'
      out_1 = yaml.safe_load(run_bash(cmd_1))
      existing_apis = []
      for i in range(0, len(out_1['items'])):
         existing_apis.append(out_1['items'][i]['name'])

      # if API for lambda has not been created before run through workflow
      if api_name not in existing_apis:
         # create api and save its id
         # cmd_2 = f'aws apigateway create-rest-api --name {api_name} --description "{api_desc}" --endpoint-configuration types="PRIVATE",vpcEndpointIds="	vpce-06b1a8f32f70b1b16" --policy file://policy.json'
         # cmd_2 = f'aws apigateway create-rest-api --name {api_name} --description "{api_desc}" --policy file://policy.json '
         cmd_2 = f'aws apigateway create-rest-api --name {api_name} --description "{api_desc}"'
         out_2 = run_bash(cmd_2)
         api_id = yaml.safe_load(out_2)['id']
         print('my api_id is: ' + api_id)

         # run get resources to get resource_id
         cmd_3 = f'aws apigateway get-resources --rest-api-id "{api_id}"'
         out_3 = run_bash(cmd_3)
         parent_id = yaml.safe_load(out_3)['items'][0]['id']
         print('my_api_parent_id is: ' + parent_id)

         # create resource
         cmd_4 = f'aws apigateway create-resource --rest-api-id {api_id} --parent-id {parent_id} --path-part {{proxy+}}'
         out_4 = run_bash(cmd_4)
         resource_id = yaml.safe_load(out_4)['id']
         print(out_4)

         # apply put-method to api
         cmd_5 = f'aws apigateway put-method --rest-api-id {api_id} --resource-id {resource_id} --http-method "ANY" --authorization-type "NONE"'
         out_5 = run_bash(cmd_5)
         print(out_5)
         
         # apply put-integration to api, note: look into differences between AWS and AWS_PROXY. response body seems to change slightly.
         cmd_6 = f'aws apigateway put-integration --rest-api-id {api_id} --resource-id {resource_id} --http-method ANY --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_url}/invocations"'
         out_6 = run_bash(cmd_6)
         print(out_6)

         # give lambda permissions to be run by your api.
         cmd_7 = f'aws lambda add-permission --function-name {function_aws} --statement-id "{api_id}" --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:us-east-1:482102633168:{api_id}/*"'
         out_7 = run_bash(cmd_7)
         print(out_7)

         # add a usage plan and associate 
         cmd_a = f'aws apigateway create-usage-plan --name "New Usage Plan" --description "A new usage plan" --api-stages '

         cmd_b = f'aws apigateway create-usage-plan-key --usage-plan-id s265ki --key-id n5xcajk4ck --key-type "API_KEY"'
         
         # deploy api to connect lambda with api gateway
         cmd_8 = f'aws apigateway create-deployment --rest-api-id {api_id} --stage-name "dev"'
         out_8 = run_bash(cmd_8)
         print(out_8)
         

# TO DO, FOR DEMO 2/1
# 1. make the create_usage_plans commands dynamic. The plan_key requires the plan Id from the first commmand. apply throttle limits



# TO DEMO ON 2/8
# 2. register a new domain, sample-apis-von.com  (or something similar to this)
# 3. make sure the right route 53 routes show up here for this (might not have to do anything)
# 4. make a new domain for the api in api gateway, named apis.sample-apis-von.com. This willl prompt you to make new certificate
# 5. Make the new certificate, and then validate it. This is a manual step that needs to be done using the certificates manager
# 6. use the new cert with the apis.sample... domain.
# 7. user the endpoint api gateway domain name given to you and create a record in route 53 that maps to this

# make two new lambdas, name them key-api-101 and key-api-102

# 8. create an api mapping to a path named dev/key-api-101
# 9. create an api mapping to a path named dev/key-api-102

# 10. we should now be able to curl via the following:
# working example: curl -H "x-api-key:abc123abc123abc123abc123" https://apis.mengpotato.com/dev/hello-world/placeholder\?name\=bryan
# for this new api: curl -H "x-api-key:abc123abc123abc123abc123" https://apis.sample-apis-von.com/dev/key-api-101/get\?name\=bryan
# curl -H "x-api-key:abc123abc123abc123abc123" https://0sp5tjjwu2.execute-api.us-east-1.amazonaws.com/dev/place\?name\=bryan 