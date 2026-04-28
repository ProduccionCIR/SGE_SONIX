def get_user(self, usuario):
        """Busca un usuario por su nombre de usuario en la tabla perfiles."""
        try:
            # Cambiamos la tabla a 'perfiles' y el filtro a 'usuario'
            res = self.supabase.table("perfiles").select("*").eq("usuario", usuario).execute()
            
            # Retorna el primer registro si existe, sino None
            return res.data[0] if res.data else None
        except Exception as e:
            st.error(f"Error al obtener usuario: {e}")
            return None