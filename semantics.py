from api import completion, Model, response
from utils import log, LogType, percent_of_string

def cardinal_to_ordinal(cardinal: int, **kwargs) -> str:
    return completion(
        model=Model.instruct,
        prompt=f"""
        Task: Convert a cardinal number into its positional ordinal adjective.
        ---
        Example1.
        Cardinal: '7745'
        Ordinal: 'seven thousand seven hundred forty-fifth'
        ---
        Example2.
        Cardinal: '93'
        Ordinal: 'ninety-third'
        ---
        Example3.
        Cardinal: '581'
        Ordinal: 'five hundred eighty-first'
        ---
        Example4.
        Cardinal: '{str(cardinal)}'
        Ordinal: '""",
        stop=["'"],
        temperature=kwargs.get("temperature", 0.0),
        top_p=kwargs.get("top_p", 0.0),
        min_p=kwargs.get("min_p", 1),
        **kwargs
    )

def generate_questions(prompt: str, q_count: int = 5, as_string: bool = False, show_progress: bool = False, **kwargs) -> list | str:
    """
    Slow and token-hefty but stable.
    """
    questions = []
    for q in range(q_count):
        if questions:
            _questions = "\n".join(questions) + "\n" + f"{q+1}. "
        else:
            _questions = "1. "
            
        new_question = completion(
            model=Model.instruct,
            prompt=f"""
            Logic Task: Ask the given number of most relevant standalone questions focusing on the key elements, related frames, and presuppositions within the Query.
            Use deductive reasoning, pragmatic inference, and individuation.
            Attempt to simulate the scenario of the Query in your head, and observing what happens.
            Identify the primary subjects, actions, and context, activate associated frames to grasp typical scenarios, infer common ground and contextual assumptions, and generate questions that explore implied causes, relationships, constraints, and interactions.
            ---
            Example1.
            Query: The tallest mountain in the universe.
            Question count: 5
            Questions:
            1. How do we define "tallest" when referring to a mountain in the context of the universe?
            2. What criteria are we using to determine the "universe" in this context?
            3. Are we including structures like volcanoes on celestial bodies other than Earth in our search for the tallest mountain in the universe?
            4. Given the vastness of the universe, what methods or technologies do astronomers or astrophysicists use to identify and measure the height of mountains on celestial bodies beyond Earth?
            5. How do extreme conditions like gravity, atmospheric pressure, and surface composition on celestial bodies impact the formation and measurement of mountains, potentially affecting our definition of "tallest" in the universe?
            ---
            Example2.
            Query: I have 4 shirts that took 3 hours to dry in the sun. How long would it take for 5 shirts?
            Question count: 3
            Questions:
            1. What factors might influence the drying time of shirts in the sun, and how do these factors scale when going from 4 shirts to 5 shirts?
            2. Are there any assumptions we can make about the consistency of the weather conditions or fabric types that could affect the drying time of the shirts?
            3. Assuming all shirts are the same, and environmental factors remain unvaried, wouldn't the drying time remain unchanged?
            ---
            Example3.
            Query: {prompt}
            Question count: {q_count}
            Questions:
            {_questions}""",
            temperature=kwargs.get("temperature", 0.6),
            top_p=kwargs.get("top_p", 0.6),
            min_p=kwargs.get("min_p", 0.6),
            frequency_penalty=0.3,
            presence_penalty=0.5,
            stop=["\n"],
            **kwargs
        )
        
        questions.append(f"{q+1}. {new_question}")
        
        if show_progress:
            log(LogType.think, f"[Semantics] Questions ({q+1}/{q_count}): {percent_of_string(new_question, 50)}...")
        
    if as_string:
        return "\n".join(questions)
    else:
        return questions

def summarize(content_type: str, content: str, extra_inst: str = None):
    if extra_inst:
        extra = extra_inst
    else:
        extra = ""
    return response(
        system=f"""
            You are a {content_type} summarizer.
            Return a summarized version of the content provided by the user.
            {extra}
        """,
        prompt=content,
        model=Model.long_context,
        temperature=0.6,
        top_p=0.3,
        frequency_penalty=0.2,
        presence_penalty=0.2
    )