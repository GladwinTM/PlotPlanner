-- PlotPlanner demo workspace. Run only against the intended project database.
-- The account is deliberately a shared, non-sensitive demo: demo@plotplanner.app
begin;

-- Refuse to overwrite a pre-existing account. Re-seeding requires an explicit,
-- separately reviewed maintenance action; this script is intentionally create-only.
do $$
begin
  if exists (select 1 from auth.users where email = 'demo@plotplanner.app') then
    raise exception 'demo@plotplanner.app already exists; refusing to overwrite it';
  end if;
end $$;

with demo as (
  select 'd0000000-0000-4000-8000-000000000001'::uuid as id,
         'demo@plotplanner.app'::text as email
)
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  confirmation_token, recovery_token, email_change_token_new, email_change,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
)
select '00000000-0000-0000-0000-000000000000', id, 'authenticated', 'authenticated', email,
       crypt('PlotPlannerDemo!2026', gen_salt('bf')), now(),
       '', '', '', '',
       jsonb_build_object('provider', 'email', 'providers', jsonb_build_array('email')),
       jsonb_build_object('display_name', 'Maya Chen'), now(), now()
from demo;

with demo as (select 'd0000000-0000-4000-8000-000000000001'::uuid as id)
insert into auth.identities (provider_id, user_id, identity_data, provider, created_at, updated_at)
select 'demo@plotplanner.app', id,
       jsonb_build_object('sub', id::text, 'email', 'demo@plotplanner.app', 'email_verified', true, 'phone_verified', false),
       'email', now(), now()
from demo;

insert into public.profiles (
  user_id, display_name, location, current_occupation, education_summary, experience_summary,
  available_hours_per_week, learning_preferences, constraints_summary, onboarding_completed
) values (
  'd0000000-0000-4000-8000-000000000001', 'Maya Chen', 'Bengaluru, India', 'Product designer and community workshop host',
  'B.Des in Interaction Design. Ongoing self-directed study in creative coding, accessibility, and urban gardening.',
  'Five years designing approachable digital products. Maya facilitates monthly sketching circles and has shipped two small community tools.',
  8, 'Learns best through short projects, visual notes, and a mix of reading with hands-on practice.',
  'Evenings and Saturday mornings are most reliable. Prefers small, sustainable commitments and public learning with kind peers.', true
);

insert into public.profile_facts (id, user_id, kind, value, detail, source, confirmed) values
  ('d1000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','skill','Product design','Research synthesis, interaction flows, and accessible interface craft.','manual',true),
  ('d1000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','skill','Figma and prototyping','Creates testable prototype flows and clear handoff notes.','manual',true),
  ('d1000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000001','skill','Facilitation','Hosts welcoming small-group creative workshops.','manual',true),
  ('d1000000-0000-4000-8000-000000000004','d0000000-0000-4000-8000-000000000001','project','Neighbourhood seed library','Designed the first checkout flow and volunteer handbook.','manual',true),
  ('d1000000-0000-4000-8000-000000000005','d0000000-0000-4000-8000-000000000001','preference','Project-led learning','Prefers a small public artifact over long lecture sequences.','manual',true);

insert into public.interests (id,user_id,name,description,category,interest_type,node_kind,priority,source,seeks_income,position_x,position_y) values
  ('d2000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','Product design','Making useful digital things feel clear and humane.','Design','professional','main',5,'manual',true,80,130),
  ('d2000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','Creative coding','Small interactive sketches made with code.','Creative technology','creative','main',5,'manual',true,350,80),
  ('d2000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000001','Accessible design','Designing for different bodies, contexts, and ways of using technology.','Design','professional','secondary',4,'manual',false,130,330),
  ('d2000000-0000-4000-8000-000000000004','d0000000-0000-4000-8000-000000000001','Community workshops','Creating low-pressure spaces to make and learn together.','Community','personal','secondary',4,'manual',true,440,300),
  ('d2000000-0000-4000-8000-000000000005','d0000000-0000-4000-8000-000000000001','Urban gardening','Growing food and noticing local ecosystems.','Nature','personal','skill',3,'manual',false,650,175);

insert into public.interest_relationships (id,user_id,source_interest_id,target_interest_id,relationship_type) values
  ('d3000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','d2000000-0000-4000-8000-000000000001','d2000000-0000-4000-8000-000000000003','supports'),
  ('d3000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','d2000000-0000-4000-8000-000000000002','d2000000-0000-4000-8000-000000000004','shares_skills_with'),
  ('d3000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000001','d2000000-0000-4000-8000-000000000004','d2000000-0000-4000-8000-000000000005','related_to');

insert into public.goals (id,user_id,title,description,category,target_outcome,priority,status,target_date,hours_per_week,interest_id,plan_summary) values
  ('d4000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','Publish an accessible garden-planner prototype','Turn a local growing guide into a usable, mobile-friendly planning prototype.','creative','A tested prototype and a short case study.',5,'active',current_date + 35,4,'d2000000-0000-4000-8000-000000000001','Build in small weekly slices, test with two gardeners, then write up the learning.'),
  ('d4000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','Run a creative-coding sketch night','Host one welcoming, beginner-friendly making session.','community','Twelve participants leave with a small interactive sketch.',4,'active',current_date + 21,2,'d2000000-0000-4000-8000-000000000004','Prepare a tiny starter sketch, a one-page guide, and a relaxed facilitation plan.'),
  ('d4000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000001','Refresh my accessibility practice','Complete an accessibility review of a recent product flow.','learning','A concise audit with concrete improvements.',3,'completed',current_date - 7,2,'d2000000-0000-4000-8000-000000000003','Completed through a focused audit and team share-out.');

insert into public.goal_milestones (id,goal_id,user_id,title,position,due_date,completed_at,source) values
  ('d5000000-0000-4000-8000-000000000001','d4000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','Map the gardener journey',1,current_date - 7,now() - interval '10 days','manual'),
  ('d5000000-0000-4000-8000-000000000002','d4000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','Prototype the weekly plan',2,current_date + 7,null,'manual'),
  ('d5000000-0000-4000-8000-000000000003','d4000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','Test with two neighbours',3,current_date + 21,null,'manual'),
  ('d5000000-0000-4000-8000-000000000004','d4000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','Choose the prompt and starter sketch',1,current_date - 3,now() - interval '4 days','manual'),
  ('d5000000-0000-4000-8000-000000000005','d4000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','Invite the group',2,current_date + 4,null,'manual'),
  ('d5000000-0000-4000-8000-000000000006','d4000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000001','Audit the focus flow',1,current_date - 20,now() - interval '18 days','manual'),
  ('d5000000-0000-4000-8000-000000000007','d4000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000001','Share improvements with the team',2,current_date - 10,now() - interval '8 days','manual');

insert into public.goal_checkins (id,goal_id,user_id,note,minutes,created_at)
select gen_random_uuid(), 'd4000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001',
       'Made a small, concrete step on the garden-planner prototype.', 45 + (n % 3) * 15, now() - (n || ' days')::interval
from generate_series(2, 38, 6) as n;

insert into public.courses (id,user_id,interest_id,goal_id,title,description,objective,difficulty,estimated_hours,prerequisites,focus,status) values
  ('d6000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','d2000000-0000-4000-8000-000000000002','d4000000-0000-4000-8000-000000000002','Creative coding for welcoming workshops','A small, project-led pathway for making and facilitating a browser sketch.','Create a friendly interactive sketch and guide others through remixing it.','beginner',12,'Comfortable using a browser and text editor.','For a community sketch night','ready'),
  ('d6000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','d2000000-0000-4000-8000-000000000003','d4000000-0000-4000-8000-000000000003','Practical accessibility review','A focused accessibility review pathway grounded in one real product flow.','Identify barriers and write implementable improvements.','intermediate',8,'A product flow to inspect.','For product design practice','ready');

insert into public.course_modules (id,course_id,position,title,description,learning_objectives,completion_criteria,required,resource_queries) values
  ('d7000000-0000-4000-8000-000000000001','d6000000-0000-4000-8000-000000000001',0,'Make a tiny sketch','Start with one responsive visual idea.','Use variables and events to make a simple change.','A working sketch responds to input.',true,'["creative coding starter sketch"]'),
  ('d7000000-0000-4000-8000-000000000002','d6000000-0000-4000-8000-000000000001',1,'Design a remix prompt','Shape an invitation that lowers the barrier to making.','Write clear prompts and leave room for personal choices.','A one-page remix guide is ready.',true,'["workshop facilitation creative coding"]'),
  ('d7000000-0000-4000-8000-000000000003','d6000000-0000-4000-8000-000000000001',2,'Host and reflect','Run a short test with a friend.','Observe where people hesitate and revise.','Three notes inform the next version.',true,'["reflective facilitation"]'),
  ('d7000000-0000-4000-8000-000000000004','d6000000-0000-4000-8000-000000000002',0,'Inspect the flow','Review keyboard, focus, labels, and contrast.','Find barriers with a repeatable checklist.','An audit captures concrete observations.',true,'["web accessibility review"]'),
  ('d7000000-0000-4000-8000-000000000005','d6000000-0000-4000-8000-000000000002',1,'Share improvements','Translate findings into respectful implementation notes.','Prioritize fixes by impact.','A team-ready improvement list exists.',true,'["accessible design handoff"]');

insert into public.course_activities (id,module_id,position,kind,title,instructions,estimated_minutes) values
  ('d8000000-0000-4000-8000-000000000001','d7000000-0000-4000-8000-000000000001',0,'lesson','Read the sketch anatomy','Notice input, output, and one variable.','15'),
  ('d8000000-0000-4000-8000-000000000002','d7000000-0000-4000-8000-000000000001',1,'exercise','Make one interaction','Add a click or key response to the sketch.','30'),
  ('d8000000-0000-4000-8000-000000000003','d7000000-0000-4000-8000-000000000002',0,'project','Draft the remix card','Create a simple card that invites three kinds of variation.','45'),
  ('d8000000-0000-4000-8000-000000000004','d7000000-0000-4000-8000-000000000002',1,'reflection','Check the invitation','Ask whether a first-timer can begin without explanation.','15'),
  ('d8000000-0000-4000-8000-000000000005','d7000000-0000-4000-8000-000000000003',0,'project','Run a friendly test','Invite one person to remix the sketch.','45'),
  ('d8000000-0000-4000-8000-000000000006','d7000000-0000-4000-8000-000000000004',0,'assessment','Audit keyboard travel','Walk the selected product flow with a keyboard.','30'),
  ('d8000000-0000-4000-8000-000000000007','d7000000-0000-4000-8000-000000000004',1,'exercise','Review focus and labels','Record three improvements with evidence.','30'),
  ('d8000000-0000-4000-8000-000000000008','d7000000-0000-4000-8000-000000000005',0,'project','Write the improvement note','Summarise findings in implementation-ready language.','45');

insert into public.enrollments (id,user_id,course_id,status,started_at,completed_at) values
  ('d9000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','d6000000-0000-4000-8000-000000000001','active',now()-interval '28 days',null),
  ('d9000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','d6000000-0000-4000-8000-000000000002','completed',now()-interval '45 days',now()-interval '7 days');

insert into public.activity_completions (id,user_id,activity_id,notes,completed_at) values
  ('da000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','d8000000-0000-4000-8000-000000000001','Noticed how much a visible state change helps. ',now()-interval '24 days'),
  ('da000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','d8000000-0000-4000-8000-000000000002','Made the interaction deliberately simple.',now()-interval '21 days'),
  ('da000000-0000-4000-8000-000000000003','d0000000-0000-4000-8000-000000000001','d8000000-0000-4000-8000-000000000003','The remix card gives people a clear first move.',now()-interval '14 days'),
  ('da000000-0000-4000-8000-000000000004','d0000000-0000-4000-8000-000000000001','d8000000-0000-4000-8000-000000000006','Found two keyboard traps in the original flow.',now()-interval '16 days'),
  ('da000000-0000-4000-8000-000000000005','d0000000-0000-4000-8000-000000000001','d8000000-0000-4000-8000-000000000007','Paired each issue with a useful recommendation.',now()-interval '12 days'),
  ('da000000-0000-4000-8000-000000000006','d0000000-0000-4000-8000-000000000001','d8000000-0000-4000-8000-000000000008','Shared the note with the product team.',now()-interval '8 days');

insert into public.opportunities (id,user_id,opportunity_type,title,company,description,source,canonical_url,location,employment_type,compensation_text,compensation_basis,external_id,retrieved_at,fit_level,fit_reason,status) values
  ('db000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','freelance','Accessible design audit','Civic Studio','A small accessibility review for a public-interest service.','demo','https://example.com/demo-accessibility-audit','Remote','Contract','₹45,000 per project','employer_provided','demo-accessibility-audit',now(),'ready_now','Matches Maya’s established accessibility review practice.','saved'),
  ('db000000-0000-4000-8000-000000000002','d0000000-0000-4000-8000-000000000001','service_business','Creative coding facilitator','Neighbourhood Lab','Facilitate a gentle introductory sketching-with-code session.','demo','https://example.com/demo-creative-coding-facilitator','Bengaluru','Part-time','₹3,000 per session','employer_provided','demo-creative-coding-facilitator',now(),'ready_now','Builds directly on Maya’s workshop and creative-coding interests.','applied');

insert into public.earning_plans (id,user_id,interest_id,title,kind,plan) values
  ('dc000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','d2000000-0000-4000-8000-000000000003','A small accessibility-audit offer','freelance',
   '{"readiness":"Maya already has a focused audit example and facilitation experience.","offer":"A short, fixed-scope accessibility review with a practical improvement note.","who_pays":"Small product teams and community organisations with public-facing services.","portfolio":"Turn the garden-planner audit into a concise case study.","test_demand":"Offer two friendly pilot reviews through existing community contacts.","costs_and_pricing":"Keep scope to one flow and price the first pilot clearly.","evaluate_results":"Track conversations, completed reviews, and repeat requests.","improve_next":"Refine the checklist from real feedback.","what_you_need":["A one-page scope","An audit checklist","A sample improvement note"],"find_customers":["Community organisations","Early-stage product teams"],"first_week":["Prepare the sample audit","Share the offer with two contacts"],"cautions":["Keep the first scope modest","Do not overpromise compliance"]}'::jsonb);

commit;

select 'demo workspace ready' as status,
  (select count(*) from public.interests where user_id = 'd0000000-0000-4000-8000-000000000001') as interests,
  (select count(*) from public.goals where user_id = 'd0000000-0000-4000-8000-000000000001') as goals,
  (select count(*) from public.activity_completions where user_id = 'd0000000-0000-4000-8000-000000000001') as completed_activities;
