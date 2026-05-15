C     Teste extra: Sequencia de Fibonacci
      PROGRAM FIBONACCI
      INTEGER N, I, A, B, TEMP
      PRINT *, 'Quantos termos da sequencia de Fibonacci?'
      READ *, N
      A = 0
      B = 1
      PRINT *, 'Sequencia: '
      DO 40 I = 1, N
        PRINT *, A
        TEMP = A + B
        A = B
        B = TEMP
  40  CONTINUE
      END
