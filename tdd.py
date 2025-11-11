from typing import List

# --- 1단계: 테스트 대상 함수 (실제 구현) ---

def split_message(text: str, max_length: int) -> List[str]:
    """
    주어진 텍스트를 max_length를 초과하지 않는 청크로 분할합니다.
    1. 줄바꿈(\n)을 우선적으로 존중하며 묶습니다.
    2. 줄바꿈이 없는 긴 줄은 max_length에서 강제로 분할합니다.
    """
    
    # 0. 빈 문자열 엣지 케이스 처리
    if not text:
        return []

    # --- 알고리즘 1단계: 사전 분할 (Fundamental Lines 생성) ---
    # 텍스트를 \n 기준으로 먼저 나누고(original_lines),
    # max_length를 초과하는 줄은 강제로 추가 분할합니다(fundamental_lines).
    
    fundamental_lines = []
    original_lines = text.splitlines() # \n 문자를 제거하며 분리

    for line in original_lines:
        if len(line) <= max_length:
            fundamental_lines.append(line)
        else:
            # 이 줄은 max_length보다 길므로 강제 분할
            i = 0
            while i < len(line):
                fundamental_lines.append(line[i : i + max_length])
                i += max_length

    # --- 알고리즘 2단계: 재결합 (Final Chunks 생성) ---
    # "사전 분할"된 줄(fundamental_lines)들을 순회하며,
    # max_length를 넘지 않는 선에서 최대한 \n으로 다시 묶습니다.

    if not fundamental_lines:
        # (예: 입력 텍스트가 "\n"만 있었던 경우)
        # splitlines()는 빈 리스트를 반환하지 않고 ['']를 반환할 수 있으나,
        # 만약 fundamental_lines가 비었다면 빈 리스트 반환 (로직 수정)
        # text.splitlines()는 ["", ""] 등을 반환할 수 있음.
        #
        # Re-check: text="\n" -> original_lines=[''] -> fundamental_lines=['']
        # Re-check: text="\n\n" -> original_lines=['', ''] -> fundamental_lines=['', '']
        # 따라서 fundamental_lines가 비는 경우는 없음 (입력 텍스트가 ""일 때 제외, 이미 처리됨)
        pass

    final_chunks = []
    current_chunk_lines = [] # 현재 묶고 있는 줄들

    for line in fundamental_lines:
        if not current_chunk_lines:
            # 현재 청크가 비어있으면 이 줄을 무조건 추가
            current_chunk_lines.append(line)
            continue

        # 현재 청크에 새 줄을 '\n'과 함께 추가했을 때의 예상 길이 계산
        # (기존 청크 길이) + (추가될 \n 개수) + (새 줄 길이)
        # "\n".join()을 사용하는 것이 가장 정확함
        
        # [수정] 더 효율적인 계산:
        # 기존 청크 길이 = len("\n".join(current_chunk_lines))
        # 새 청크 길이 = 기존 청크 길이 + 1 (줄바꿈) + len(line)
        existing_length = len("\n".join(current_chunk_lines))
        projected_length = existing_length + 1 + len(line)

        if projected_length <= max_length:
            # 길이 제한 OK. 현재 청크에 이 줄을 추가
            current_chunk_lines.append(line)
        else:
            # 길이 제한 초과.
            # 1. 지금까지 묶은 청크(current_chunk_lines)를 확정하여 final_chunks에 추가
            final_chunks.append("\n".join(current_chunk_lines))
            # 2. 현재 줄(line)로 새 청크 시작
            current_chunk_lines = [line]

    # 루프가 끝난 후, current_chunk_lines에 남아있는 마지막 청크를 추가
    if current_chunk_lines:
        final_chunks.append("\n".join(current_chunk_lines))

    return final_chunks