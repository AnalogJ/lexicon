<h1>Provider Specification</h1>

[TOC]

# General
- **name** Any record name supplied to the provider must be the full hostname.
- **ttl** Reasonable default is 6 hours since it's supported by most services. Any service that does not support this must be explicitly mentioned somewhere.

# API Operations
## create_record
- **Normal Behavior** Create a new DNS record.
- **If Record Already Exists** Do nothing. **DO NOT** throw exception.
- **TTL** If not specified or set to `0`, use reasonable default.
- **Record Sets** If service has provisions for record sets, **DO NOT** remove any existing records in the set.

## list_record
- **Normal Behaviour** List all records. Apply filter as required.
- **Record Sets** Read all record sets and add a record entry as follows:  {name:'', type:'', content: ''}. **DO NOT** bundle together record sets and treat as one record.
- **Linked Records** For services that support some form of linked record, do not resolve, treat as CNAME.

## update_record
- **Normal Behaviour** Update a record matching name, type and content.
- **Record Sets** If matched record is part of a record set, only update the record that matches. **DO NOT** modify other records in any way. Update the record set so that records other than the matched one are unmodified.
- **TTL**
    - If not specified, do not modify ttl.
    - If set to `0`, reset to reasonable default.
- **No Match** Throw exception?

## delete_record
- **Normal Behaviour** Remove a record from the service.
- **Record sets** Remove only the record that matches all the filters. 
    - If content is not specified, remove the record set.
    - If length of record set becomes 0 after removing record, remove the record set.
- **No Match** Do nothing. **DO NOT** throw exception

# Record Set Handling (Clarification)
Normally, a record set is formed from the combination of the name and type fields (on most services). Extra clarifications for handling these are given below.

## create_record
### No record set exists with the same name and type
Create a record set with 1 record.
`{'name':'example.com', 'type':'A', 'records':[ '127.0.0.1' ]}`

### Record set exists with same name and type
Add the content of the new record to the record set.
If service returns this:
`{'name':'example.com', 'type':'A', 'records':[ '127.0.0.1' ]}`
and `create_record('example.com','A','127.0.0.2')` is called, modify to this:
`{'name':'example.com', 'type':'A', 'records':[ '127.0.0.1', '127.0.0.2' ]}`

**NOTE** Existing data not modified

## list_record
Read all records within a set and return them as individual records.

If service returns this:

`{'name':'example.com', 'type':'A', 'records':[ '127.0.0.1', '127.0.0.2' ]}`

Provider should return this:

`[{'name':'example.com', 'type':'A', 'content': '127.0.0.1'},
{'name':'example.com', 'type':'A', 'content': '127.0.0.2'}]`

## update_record
Update only the record that matches the filter content.

If current value is this:

`{'name':'example.com', 'type':'A', 'records':[ '127.0.0.1', '127.0.0.2' ]}`

and `update_record('example.com','A','127.0.0.1','127.1.0.1')` is called, modify to this:

`{'name':'example.com', 'type':'A', 'records':[ '127.1.0.1', '127.0.0.2' ]}`

**Do not modify/remove other records in the set**

## delete_record
Remove only the record that matches the filters.

If current value is this:

`{'name':'example.com', 'type':'A', 'records':[ '127.0.0.1', '127.0.0.2' ]}`

and `delete_record('example.com','A','127.0.0.1')` is called, modify to this:

`{'name':'example.com', 'type':'A', 'records':[ '127.0.0.2' ]}`

**Remove the record set only if `content` is not specified or length of `records` become 0 after removing record**