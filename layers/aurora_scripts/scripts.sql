CREATE TABLE public.user_table (
	user_id varchar NOT NULL,
	full_name varchar NOT NULL,
	user_type varchar NOT NULL,
	email varchar NOT NULL,
	tenant_id varchar NOT NULL,
	CONSTRAINT user_table_pk PRIMARY KEY (user_id)
);

CREATE TABLE public.course_table (
	course_id varchar NOT NULL,
	teacher_id varchar NOT NULL,
	course_name varchar NOT NULL,
	course_description varchar NOT NULL,
	CONSTRAINT course_table_pk PRIMARY KEY (course_id),
	CONSTRAINT course_table_fk FOREIGN KEY (teacher_id) REFERENCES public.user_table(user_id)
);

CREATE TABLE public.course_asistants (
	course_id varchar NOT NULL,
	student_id varchar NOT NULL,
	CONSTRAINT course_asistants_fk FOREIGN KEY (course_id) REFERENCES public.course_table(course_id),
	CONSTRAINT course_asistants_fk_1 FOREIGN KEY (student_id) REFERENCES public.user_table(user_id)
);

CREATE TABLE public.course_grades (
	course_id varchar NOT NULL,
	student_id varchar NOT NULL,
	course_grade decimal NOT NULL,
	CONSTRAINT course_grades_fk FOREIGN KEY (course_id) REFERENCES public.course_table(course_id),
	CONSTRAINT course_grades_fk_1 FOREIGN KEY (student_id) REFERENCES public.user_table(user_id)
);

