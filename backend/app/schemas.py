from pydantic import BaseModel, ConfigDict, Field

FIELDS = {
    'project_id':'Project identifier','project_name':'Project name',
    'land_required':'Land required','land_acquired':'Land acquired',
    'sanction_amount':'Sanction amount','sanction_date':'Sanction date',
    'date_3a':'3a notification date','date_3A':'3A notification date','date_3D':'3D notification date',
    'observation_date':'Observation / input snapshot date','source_date':'Source publication / update date',
    'source_reference':'Source reference','planned_completion':'Planned completion date',
    'actual_completion':'Actual completion date'
}
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')
class Upload(Strict):
    csv_text:str=Field(min_length=1,max_length=5_000_000)
class Settings(Strict):
    mapping:dict[str,str]
    area_unit:str=Field(pattern='^(hectares|acres|square_metres)$')
    date_format:str=Field(pattern='^(ISO|DMY|MDY)$')
    project_type:str=Field(pattern='^(highway|other)$')
    amount_unit:str=Field(pattern='^(INR|INR_lakh|INR_crore)$')
    comparable_scope:bool=False
    distinct_projects:bool=False
class Analysis(Upload):
    settings:Settings
class WhatIf(Analysis):
    row_index:int=Field(ge=0)
    acquired:float=Field(ge=0,allow_inf_nan=False)
class Export(Analysis):
    notes:dict[str,str]=Field(default_factory=dict,max_length=10000)
    include_notes:bool=False
class Train(Analysis):
    verified_outcomes:bool=False
    verified_snapshot_inputs:bool=False
    verified_plan_at_snapshot:bool=False
    verification_note:str=Field(default='',max_length=2000)
