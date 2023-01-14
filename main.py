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

   # deploy the lambdas that are indicated as such
   for cur_lambda in lambdas_to_deploy:
      # extract data from yamls
      api_name = cur_lambda['name']
      api_desc = cur_lambda['description']
      api_url = cur_lambda['url']
      
      # get list of existing APIs
      cmd_1 = 'aws apigateway get-rest-apis'
      out_1 = yaml.safe_load(run_bash(cmd_1))
      existing_apis = []
      for i in range(0, len(out_1['items'])):
         existing_apis.append(out_1['items'][i]['name'])
      
      # if API for lambda has not been created before run through workflow
      if api_name not in existing_apis:
         # create api and save its id
         cmd_2 = f'aws apigateway create-rest-api --name {api_name} --description "{api_desc}"'
         out_2 = run_bash(cmd_2)
         api_id = yaml.safe_load(out_2)['id']
         print('my api_id is: ' + api_id)

         # run get resources to get resource_id
         cmd_3 = f'aws apigateway get-resources --rest-api-id "{api_id}"'
         out_3 = run_bash(cmd_3)
         resource_id = yaml.safe_load(out_3)['items'][0]['id']
         print('my_api_parent_id is: ' + resource_id)

         # apply put-method to api
         cmd_4 = f'aws apigateway put-method --rest-api-id "{api_id}" --resource-id "{resource_id}" --http-method "GET" --authorization-type "NONE" --no-api-key-required'
         out_4 = run_bash(cmd_4)

         # apply put-method-response to api
         cmd_5 = f'aws apigateway put-method-response --rest-api-id "{api_id}" --resource-id "{resource_id}"  --http-method GET --status-code 200' # --response-models "{\"application/json\": \"Empty\"}"
         out_5 = run_bash(cmd_5)

         # apply put-integration to api, note: look into differences between AWS and AWS_PROXY. response body seems to change slightly.
         cmd_6 = f'aws apigateway put-integration --rest-api-id "{api_id}" --resource-id "{resource_id}" --http-method GET --type AWS --integration-http-method POST --uri "arn:aws:apigateway:us-west-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-1:482102633168:function:my_awscli_function/invocations"'
         out_6 = run_bash(cmd_6)
         print(out_6)

         # apply put-integration-response to api 
         cmd_7 = f'aws apigateway put-integration-response --rest-api-id "{api_id}" --resource-id "{resource_id}" --http-method GET --status-code 200 --content-handling CONVERT_TO_TEXT'
         out_7 = run_bash(cmd_7)
         print(out_7)

         # give lambda permissions to be run by your api.
         cmd_8 = f'aws lambda add-permission --function-name my_awscli_function --statement-id apigateway-test-1 --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:us-west-1:482102633168:{api_id}/*/GET/"'
         out_8 = run_bash(cmd_8)
         print(out_8)

         # deploy api to connect lambda with api gateway
         cmd_9 = f'aws apigateway create-deployment --rest-api-id "{api_id}" --stage-name "dev"'
         out_9 = run_bash(cmd_9)
         print(out_9)

# NOTES
# for demo wednesday, I am comfortable taking this, making it slightly more dynamic / clean up, and then showcase. This handles the biggest question in the ehole process
# remianing to do:
#1. move this into work aws environment
#2. figure out how this interacts with deployment changes to existing lambdas/lambda versions
#3. further define the yaml file and whats needed to auto deploy
#4. GHA to execute this code in a runner? or we can do this locally. In its current state, a bit concerned with fully automated this process.
#5. Resolve the VPC peering, close off api gateway to the public internet.
